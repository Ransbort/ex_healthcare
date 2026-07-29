import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from ex_healthcare.ex_healthcare.workspace_installer import (
	workspace_installer,
	workspace_remover,
)


def setup():
	make_custom_fields()
	workspace_installer()


def uninstall():
	custom_fields = get_custom_fields()
	delete_custom_fields(custom_fields)
	workspace_remover()


def make_custom_fields(update=True):
	custom_fields = get_custom_fields()
	create_custom_fields(custom_fields, update=update)


def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Sales Order': [{fieldname: '', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)
		frappe.clear_cache(doctype=doctype)


def get_custom_fields():
	return {
		# Pharmacy POS: tags the Sales Order as pharmacy-originated, links it
		# to the dispensing Patient, and links each line item back to the
		# Medication Request it was dispensed against.
		#
		# custom_department: used by the Cashier Portal
		# (page/cashier_portal/cashier_portal.py) to bucket a party's open
		# orders into Pharmacy/Laboratory/Rehabilitation/Other tabs -
		# without this field, _get_department_invoices()/_get_pharmacy_orders()
		# throw "Unknown column 'custom_department'".
		"Sales Order": [
			{
				"fieldname": "custom_invoice_from",
				"label": "Invoice From",
				"fieldtype": "Select",
				"insert_after": "customer",
				"options": "\nPharmacy\nSpa",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "custom_patient",
				"label": "Patient",
				"fieldtype": "Link",
				"insert_after": "custom_invoice_from",
				"options": "Patient",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "custom_department",
				"label": "Department",
				"fieldtype": "Select",
				"insert_after": "custom_patient",
				"options": "\nPharmacy\nLaboratory\nRehabilitation\nOther",
				"reqd": 0,
				"hidden": 0,
			},
		],
		"Sales Order Item": [
			{
				"fieldname": "custom_reference_doctype",
				"label": "Reference Document Type",
				"fieldtype": "Link",
				"insert_after": "item_name",
				"options": "DocType",
				"reqd": 0,
				"hidden": 1,
			},
			{
				"fieldname": "custom_reference_name",
				"label": "Reference Name",
				"fieldtype": "Dynamic Link",
				"insert_after": "custom_reference_doctype",
				"options": "custom_reference_doctype",
				"reqd": 0,
				"hidden": 1,
			},
		],
		# Spa Portal: tags Sales Invoices created from create_spa_invoice()
		# so get_spa_invoices() can filter to spa-originated invoices only.
		#
		# custom_department: same Cashier Portal bucketing as on Sales Order
		# above, applied to Sales Invoice (_get_department_invoices() reads
		# this field on both doctypes).
		"Sales Invoice": [
			{
				"fieldname": "custom_invoice_from",
				"label": "Invoice From",
				"fieldtype": "Select",
				"insert_after": "customer",
				"options": "\nPharmacy\nSpa",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "custom_department",
				"label": "Department",
				"fieldtype": "Select",
				"insert_after": "custom_invoice_from",
				"options": "\nPharmacy\nLaboratory\nRehabilitation\nOther",
				"reqd": 0,
				"hidden": 0,
			},
		],
		# Lab Portal: priority on the requested test, and a link back to the
		# Lab Test doc created once accept_lab_request() accepts it.
		"Lab Prescription": [
			{
				"fieldname": "custom_priority",
				"label": "Priority",
				"fieldtype": "Select",
				"insert_after": "lab_test_comment",
				"options": "\nLow\nMedium\nHigh",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "custom_lab_test",
				"label": "Lab Test",
				"fieldtype": "Link",
				"insert_after": "custom_priority",
				"options": "Lab Test",
				"reqd": 0,
				"hidden": 0,
			},
		],
		# Lab Portal: links a Lab Test back to the Sales Invoice created for
		# it in accept_lab_request(). lab_portal.py's get_pending_labs() and
		# accept_lab_request() both read/write this field directly -
		# without it, get_pending_labs() throws "Unknown column
		# 'lt.custom_invoice'" since Lab Test has no built-in Sales Invoice
		# link (only a boolean `invoiced` Check field).
		"Lab Test": [
			{
				"fieldname": "custom_invoice",
				"label": "Invoice",
				"fieldtype": "Link",
				"insert_after": "invoiced",
				"options": "Sales Invoice",
				"reqd": 0,
				"hidden": 0,
			},
		],
		# Rehab Portal: same custom_invoice pattern as Lab Test above -
		# Therapy Plan has no built-in Sales Invoice link either (confirmed
		# via DESCRIBE `tabTherapy Plan`: only `invoiced` Check exists, no
		# `invoice` field). rehab_portal.py's get_pending_therapies() and
		# accept_therapy_request() both read/write custom_invoice directly.
		"Therapy Plan": [
			{
				"fieldname": "custom_invoice",
				"label": "Invoice",
				"fieldtype": "Link",
				"insert_after": "invoiced",
				"options": "Sales Invoice",
				"reqd": 0,
				"hidden": 0,
			},
		],
		# Rehab Portal: same pattern as Lab Prescription, for therapies.
		"Therapy Plan Detail": [
			{
				"fieldname": "custom_priority",
				"label": "Priority",
				"fieldtype": "Select",
				"insert_after": "interval",
				"options": "\nLow\nMedium\nHigh",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "custom_therapy_plan",
				"label": "Therapy Plan",
				"fieldtype": "Link",
				"insert_after": "custom_priority",
				"options": "Therapy Plan",
				"reqd": 0,
				"hidden": 0,
			},
		],
		# Front Desk: drives the walk-in / check-in patient journey
		# (receptionist -> nurse -> doctor).
		#
		# IMPORTANT: as of the check-in redesign, the queue lives on
		# Patient Encounter, NOT Patient Appointment. Patient Appointment
		# is now purely a schedule record (created by create_consultation()
		# with no queue/invoice state at all). The moment a patient
		# physically arrives - whether they had a booked appointment
		# (check_in_appointment()) or are a walk-in with no prior booking
		# (create_walkin_encounter()) - a draft Patient Encounter
		# (docstatus=0) is created and THAT document carries queue_status,
		# checked_in_at, vitals_*, and consultation_invoice from then on.
		# get_queue()/send_to_nurse()/save_vitals()/start_consultation() in
		# front_desk.py all read/write these fields on Patient Encounter.
		# When the doctor submits the Encounter, on_patient_encounter_submit()
		# sets queue_status to "Completed" directly on that same doc -
		# there is no longer a Patient Appointment lookup involved.
		"Patient Encounter": [
			{
				"fieldname": "queue_status",
				"label": "Queue Status",
				"fieldtype": "Select",
				"insert_after": "appointment",
				"options": "Registered\nPayment Pending\nPaid - Awaiting Vitals\nWith Nurse\nWith Doctor\nIn Consultation\nCompleted\nCancelled",
				"default": "Registered",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "front_desk_section",
				"label": "Front Desk / Nurse Station",
				"fieldtype": "Section Break",
				"insert_after": "queue_status",
				"collapsible": 1,
			},
			{
				"fieldname": "consultation_invoice",
				"label": "Consultation Invoice",
				"fieldtype": "Link",
				"insert_after": "front_desk_section",
				"options": "Sales Invoice",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "checked_in_at",
				"label": "Checked In At",
				"fieldtype": "Datetime",
				"insert_after": "consultation_invoice",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_column_break",
				"label": "",
				"fieldtype": "Column Break",
				"insert_after": "checked_in_at",
			},
			{
				"fieldname": "vitals_temperature",
				"label": "Temperature (\u00b0C)",
				"fieldtype": "Float",
				"insert_after": "vitals_column_break",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_blood_pressure",
				"label": "Blood Pressure",
				"fieldtype": "Data",
				"insert_after": "vitals_temperature",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_pulse",
				"label": "Pulse (bpm)",
				"fieldtype": "Int",
				"insert_after": "vitals_blood_pressure",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_weight",
				"label": "Weight (kg)",
				"fieldtype": "Float",
				"insert_after": "vitals_pulse",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_height",
				"label": "Height (cm)",
				"fieldtype": "Float",
				"insert_after": "vitals_weight",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_notes",
				"label": "Nurse Notes",
				"fieldtype": "Small Text",
				"insert_after": "vitals_height",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_recorded_by",
				"label": "Vitals Recorded By",
				"fieldtype": "Link",
				"insert_after": "vitals_notes",
				"options": "User",
				"reqd": 0,
				"hidden": 0,
			},
			{
				"fieldname": "vitals_recorded_on",
				"label": "Vitals Recorded On",
				"fieldtype": "Datetime",
				"insert_after": "vitals_recorded_by",
				"reqd": 0,
				"hidden": 0,
			},
		],
	}
