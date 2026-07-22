# Copyright (c) 2026, Ransbort and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _


@frappe.whitelist()
def get_pos_medications():
	"""
	Single optimized call for the Pharmacy POS grid.

	Joins Medication -> Medication Linked Item -> Item -> Item Price -> Bin
	in one query instead of the N+1 pattern used by the JS fallback
	(load_items_fallback). Returns a flat list of dicts shaped exactly like
	what render_items_grid / render_items_list expect on the frontend.
	"""

	medications = frappe.db.sql(
		"""
		SELECT
			med.name AS medication_name,
			med.generic_name AS generic_name,
			med.strength AS strength,
			med.strength_uom AS strength_uom,
			med.medication_class AS medication_class,
			med.abbr AS abbr,
			med.dosage_form AS dosage_form,
			mli.item AS item_code,
			mli.stock_uom AS stock_uom,
			item.image AS image,
			item.standard_rate AS standard_rate,
			ip.price_list_rate AS price_list_rate,
			COALESCE(stock.total_qty, 0) AS stock_qty
		FROM `tabMedication` med
		INNER JOIN `tabMedication Linked Item` mli
			ON mli.parent = med.name
		INNER JOIN `tabItem` item
			ON item.name = mli.item
		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = mli.item
			AND ip.price_list = med.price_list
		LEFT JOIN (
			SELECT item_code, SUM(actual_qty) AS total_qty
			FROM `tabBin`
			GROUP BY item_code
		) stock
			ON stock.item_code = mli.item
		WHERE med.disabled = 0
		ORDER BY med.generic_name ASC
		""",
		as_dict=True,
	)

	# de-duplicate: a Medication can have more than one linked item row,
	# only keep the first (matches the JS fallback's "if not already mapped" logic)
	seen = set()
	result = []

	for med in medications:
		if med.medication_name in seen:
			continue
		seen.add(med.medication_name)

		rate = med.price_list_rate or med.standard_rate or 0

		result.append(
			{
				"medication_name": med.medication_name,
				"generic_name": med.generic_name,
				"strength": med.strength,
				"strength_uom": med.strength_uom,
				"medication_class": med.medication_class,
				"abbr": med.abbr,
				"item_code": med.item_code,
				"rate": rate,
				"stock_uom": med.stock_uom or "Nos",
				"stock_qty": med.stock_qty or 0,
				"dosage_form": med.dosage_form or "",
				"image": med.image or "",
			}
		)

	return result


@frappe.whitelist()
def get_item_by_barcode(barcode):
	"""
	Resolve a scanned barcode to an item_code.
	Used by process_barcode() in pharmacy_pos.js for the barcode-scanner
	keypress buffer. Returns the item_code string, or None if not found.
	"""

	if not barcode:
		return None

	barcode = barcode.strip()

	item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")

	return item_code


@frappe.whitelist()
def update_medication_requests(updates, allow_oversell=False):
	"""
	Bump qty_invoiced on each Medication Request after a Sales Order is
	created + submitted from the POS. Called from process_checkout() after
	frappe.client.submit succeeds, so a failure here must never roll back
	the already-submitted Sales Order -- errors are raised back to the
	frontend, which shows a non-blocking warning (see checkout try/catch).

	Args:
		updates: JSON string or list of {"name": <Medication Request name>, "qty": <int>}
		allow_oversell: if truthy, skip the "don't exceed remaining qty" guard
			(matches Ex Healthcare Settings.allow_oversell_medication)

	IMPORTANT: each successful update is committed immediately (frappe.db.commit())
	inside the loop, rather than only at the end of the whitelisted call. If one
	Medication Request in the batch fails and we later call frappe.throw() to
	surface the aggregated errors, that throw raises an exception - and Frappe
	rolls back the *entire* request's uncommitted transaction on an unhandled
	exception. Without committing per-item, a single bad item at the end of a
	multi-item cart would silently wipe out the qty_invoiced/billing_status
	updates already applied to every other (successfully updated) Medication
	Request earlier in the same loop - even though their Sales Order had
	already been created and stock had already moved. Those medications would
	then still show billing_status = Pending/Partly Invoiced and get pulled
	back into the cart the next time "Load Prescriptions" runs for that
	patient, effectively double-counting an already-sold item.
	"""

	if isinstance(updates, str):
		updates = json.loads(updates)

	if isinstance(allow_oversell, str):
		allow_oversell = allow_oversell.lower() in ("1", "true", "yes")

	if not updates:
		return

	updated = []
	errors = []

	for update in updates:
		med_req_name = update.get("name")
		qty = frappe.utils.flt(update.get("qty"))

		if not med_req_name or qty <= 0:
			continue

		try:
			med_req = frappe.get_doc("Medication Request", med_req_name)

			total_dispensable = (
				med_req.total_dispensable_quantity or med_req.quantity or 0
			)
			already_invoiced = med_req.qty_invoiced or 0
			remaining = total_dispensable - already_invoiced

			if not allow_oversell and qty > remaining:
				errors.append(
					_(
						"Medication Request {0}: tried to invoice {1}, only {2} remaining"
					).format(med_req_name, qty, remaining)
				)
				continue

			new_qty_invoiced = already_invoiced + qty
			med_req.db_set("qty_invoiced", new_qty_invoiced, update_modified=True)

			# Keep billing_status in sync with the new invoiced quantity
			if new_qty_invoiced >= total_dispensable:
				med_req.db_set("billing_status", "Fully Invoiced", update_modified=True)
			elif new_qty_invoiced > 0:
				med_req.db_set(
					"billing_status", "Partly Invoiced", update_modified=True
				)

			# Commit NOW, per-item. This is the fix: without this, a later
			# item's failure + the frappe.throw() below would roll back this
			# (and every other already-succeeded) update in the same request,
			# even though the underlying Sales Order/stock movement already
			# happened and can't be undone. Committing per-item makes each
			# Medication Request's billing state durable independent of what
			# happens to the rest of the batch.
			frappe.db.commit()

			updated.append(med_req_name)

		except Exception:
			# Only this item's partial writes (if any) get rolled back -
			# nothing committed by prior iterations is affected.
			frappe.db.rollback()
			frappe.log_error(
				title="Pharmacy POS: update_medication_requests failed",
				message=frappe.get_traceback(),
			)
			errors.append(_("Medication Request {0}: {1}").format(med_req_name, "update failed"))

	if errors:
		# Surface partial failures to the caller; JS catches this and shows
		# a non-blocking orange warning without rolling back the Sales Order.
		# Safe to throw here now - every successful update above has already
		# been committed independently, so this exception can only affect
		# whatever wasn't committed yet (i.e. nothing, since we commit inline).
		frappe.throw(
			_("Some Medication Requests could not be fully updated:<br>{0}").format(
				"<br>".join(errors)
			)
		)

	return {"updated": updated}
