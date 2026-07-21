# Copyright (c) 2026, Ransbort and contributors
# For license information, please see license.txt

"""
Backend for the Rehab Portal page (page/rehab_portal/rehab_portal.js).
Mirrors lab_portal.py's structure exactly, mapped to therapy prescriptions
instead of lab test prescriptions.

ASSUMPTIONS TO VERIFY:

- `Patient Encounter` has a child table `therapies` (child doctype
  `Therapy Plan Detail` -- standard in ERPNext Healthcare) with fields:
  therapy_type, no_of_sessions, interval, invoiced (Check).
- `Therapy Plan Detail` has CUSTOM fields `custom_priority` and
  `custom_therapy_plan` (Link -> Therapy Plan), set once
  accept_therapy_request() creates the Therapy Plan doc.
- `Therapy Type` has an `item` field linking to a billable Item (standard
  in ERPNext Healthcare).
- `Therapy Plan` has fields: patient, therapy_plan_details (or similar),
  status, invoice. Adjust the INSERT in accept_therapy_request if your
  Therapy Plan schema stores sessions differently.
"""

import frappe
from frappe import _
from frappe.utils import today


def _rehab_search_conditions(search_patient, search_encounter, search_date, date_field="pe.encounter_date"):
	conditions = []
	values = {}

	if search_patient:
		conditions.append("(pe.patient LIKE %(search_patient)s OR pe.patient_name LIKE %(search_patient)s)")
		values["search_patient"] = f"%{search_patient}%"

	if search_encounter:
		conditions.append("pe.name = %(search_encounter)s")
		values["search_encounter"] = search_encounter

	if search_date:
		conditions.append(f"{date_field} = %(search_date)s")
		values["search_date"] = search_date

	return conditions, values


@frappe.whitelist()
def get_requested_therapies(search_patient=None, search_encounter=None, search_date=None):
	"""Therapies prescribed on an encounter but not yet accepted/invoiced."""

	conditions, values = _rehab_search_conditions(search_patient, search_encounter, search_date)
	conditions.insert(0, "tpd.invoiced = 0")
	where_clause = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			tpd.name AS therapy_id,
			tpd.therapy_type AS therapy_type,
			tpd.no_of_sessions AS no_of_sessions,
			tpd.interval AS interval,
			tpd.custom_priority AS priority,
			pe.name AS encounter_id,
			pe.patient AS patient,
			pe.patient_name AS patient_name,
			pe.encounter_date AS encounter_date,
			pe.practitioner AS practitioner,
			pe.diagnosis AS diagnosis
		FROM `tabTherapy Plan Detail` tpd
		INNER JOIN `tabPatient Encounter` pe ON pe.name = tpd.parent
		WHERE {where_clause}
		ORDER BY pe.encounter_date DESC
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def get_pending_therapies(search_patient=None, search_encounter=None, search_date=None):
	"""Accepted (invoiced) therapies whose Therapy Plan isn't Completed yet."""

	conditions, values = _rehab_search_conditions(search_patient, search_encounter, search_date)
	conditions[0:0] = [
		"tpd.invoiced = 1",
		"tpd.custom_therapy_plan IS NOT NULL",
		"tp.status != 'Completed'",
	]
	where_clause = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			tpd.name AS therapy_id,
			tpd.therapy_type AS therapy_type,
			tpd.no_of_sessions AS no_of_sessions,
			tpd.interval AS interval,
			tpd.custom_priority AS priority,
			tpd.custom_therapy_plan AS custom_therapy_plan,
			pe.name AS encounter_id,
			pe.patient AS patient,
			pe.patient_name AS patient_name,
			pe.encounter_date AS encounter_date,
			pe.practitioner AS practitioner,
			pe.diagnosis AS diagnosis,
			si.status AS invoice_status
		FROM `tabTherapy Plan Detail` tpd
		INNER JOIN `tabPatient Encounter` pe ON pe.name = tpd.parent
		INNER JOIN `tabTherapy Plan` tp ON tp.name = tpd.custom_therapy_plan
		LEFT JOIN `tabSales Invoice` si ON si.name = tp.invoice
		WHERE {where_clause}
		ORDER BY pe.encounter_date DESC
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		row["payment_status"] = "Paid" if row.pop("invoice_status", None) == "Paid" else "Unpaid"

	return rows


@frappe.whitelist()
def get_completed_therapies(search_patient=None, search_encounter=None, filter_date=None):
	"""Therapies whose Therapy Plan has been marked Completed."""

	conditions, values = _rehab_search_conditions(
		search_patient, search_encounter, filter_date, date_field="DATE(tp.modified)"
	)
	conditions[0:0] = [
		"tpd.invoiced = 1",
		"tpd.custom_therapy_plan IS NOT NULL",
		"tp.status = 'Completed'",
	]
	where_clause = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			tpd.name AS therapy_id,
			tpd.therapy_type AS therapy_type,
			tpd.custom_therapy_plan AS custom_therapy_plan,
			pe.name AS encounter_id,
			pe.patient AS patient,
			pe.patient_name AS patient_name,
			pe.encounter_date AS encounter_date,
			pe.practitioner AS practitioner,
			pe.diagnosis AS diagnosis
		FROM `tabTherapy Plan Detail` tpd
		INNER JOIN `tabPatient Encounter` pe ON pe.name = tpd.parent
		INNER JOIN `tabTherapy Plan` tp ON tp.name = tpd.custom_therapy_plan
		WHERE {where_clause}
		ORDER BY tp.modified DESC
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def accept_therapy_request(therapy_id, patient_id, encounter_id, therapy_type):
	"""
	Accept a requested therapy: create + submit a Sales Invoice, create a
	draft Therapy Plan, then stamp the originating Therapy Plan Detail row
	so it shows up under Pending instead of Requested on the next reload.
	"""

	encounter = frappe.get_doc("Patient Encounter", encounter_id)

	therapy_row = None
	for row in encounter.therapies:
		if row.name == therapy_id:
			therapy_row = row
			break

	if not therapy_row:
		frappe.throw(_("Therapy Plan Detail row {0} not found on encounter {1}").format(therapy_id, encounter_id))

	customer = frappe.db.get_value("Patient", patient_id, "customer")
	if not customer:
		frappe.throw(_("Patient {0} has no linked Customer").format(patient_id))

	item_code = frappe.db.get_value("Therapy Type", therapy_type, "item")
	if not item_code:
		frappe.throw(_("Therapy Type {0} has no linked Item").format(therapy_type))

	rate = frappe.db.get_value("Item Price", {"item_code": item_code}, "price_list_rate") or 0
	no_of_sessions = therapy_row.no_of_sessions or 1

	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer,
			"patient": patient_id,
			"posting_date": today(),
			"items": [
				{
					"item_code": item_code,
					"qty": no_of_sessions,
					"rate": rate,
					"reference_dt": "Patient Encounter",
					"reference_dn": encounter_id,
				}
			],
		}
	)
	invoice.insert(ignore_permissions=True)
	invoice.submit()

	therapy_plan = frappe.get_doc(
		{
			"doctype": "Therapy Plan",
			"patient": patient_id,
			"invoice": invoice.name,
			"status": "Draft",
			"therapy_plan_details": [
				{
					"therapy_type": therapy_type,
					"no_of_sessions": no_of_sessions,
				}
			],
		}
	)
	therapy_plan.insert(ignore_permissions=True)

	therapy_row.db_set("custom_therapy_plan", therapy_plan.name)
	therapy_row.db_set("invoiced", 1)

	return {
		"status": "Success",
		"invoice_name": invoice.name,
		"therapy_plan_name": therapy_plan.name,
	}


@frappe.whitelist()
def get_print_formats(doctype):
	formats = frappe.get_all(
		"Print Format",
		filters={"doc_type": doctype, "disabled": 0},
		fields=["name"],
		order_by="name asc",
	)
	if not any(f.name == "Standard" for f in formats):
		formats.insert(0, {"name": "Standard"})
	return formats


@frappe.whitelist()
def get_print_content(doctype, docname, print_format=None):
	html = frappe.get_print(doctype, docname, print_format=print_format or None)
	return {"html": html}
