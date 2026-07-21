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
	}
