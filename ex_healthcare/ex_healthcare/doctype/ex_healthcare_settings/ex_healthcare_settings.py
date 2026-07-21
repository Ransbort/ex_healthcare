import frappe
from frappe.model.document import Document


# Fields mirrored read-only onto Ex Healthcare Settings from Healthcare
# Settings (the "Marley Healthcare" app this app depends on). Kept as a
# single source of truth here so the mirror stays in sync automatically --
# add a fieldname to this list only after adding the matching read-only
# field to ex_healthcare_settings.json.
MIRRORED_HEALTHCARE_SETTINGS_FIELDS = [
	"link_customer_to_patient",
	"lab_test_approval_required",
	"create_lab_test_on_si_submit",
	"op_consulting_charge_item",
	"inpatient_visit_charge_item",
	"clinical_procedure_consumable_item",
]


class ExHealthcareSettings(Document):
	def onload(self):
		"""
		Pull current values from Healthcare Settings and set them on this
		in-memory doc (never saved back to the DB here) so the form always
		shows what's actually configured in Healthcare Settings -- no
		duplicated/stale data. Editing still happens in Healthcare Settings
		itself; these fields are read_only on this form.
		"""
		healthcare_settings = frappe.get_single("Healthcare Settings")

		for fieldname in MIRRORED_HEALTHCARE_SETTINGS_FIELDS:
			self.set(fieldname, healthcare_settings.get(fieldname))
