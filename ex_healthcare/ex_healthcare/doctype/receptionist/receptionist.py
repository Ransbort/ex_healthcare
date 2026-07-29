# Copyright (c) 2026, Pep Sports Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Receptionist(Document):
	def validate(self):
		self.ensure_role_assigned()

	def ensure_role_assigned(self):
		"""Auto-assign the Healthcare Receptionist role to the linked User
		so permissions stay in sync with this master record."""
		if not self.user:
			return

		user_doc = frappe.get_doc("User", self.user)
		existing_roles = {r.role for r in user_doc.get("roles")}

		if "Healthcare Receptionist" not in existing_roles:
			user_doc.append("roles", {"role": "Healthcare Receptionist"})
			user_doc.save(ignore_permissions=True)
			frappe.msgprint(
				_("Healthcare Receptionist role has been assigned to {0}").format(self.user),
				alert=True,
			)
