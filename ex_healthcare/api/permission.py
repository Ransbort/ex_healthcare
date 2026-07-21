import frappe


@frappe.whitelist()
def has_app_permission():
	"""
	Controls visibility of the Ex Healthcare icon on the Frappe app switcher
	(hooks.py: add_to_apps_screen). Return True to show it to everyone, or
	add a role check if you want to restrict it -- e.g.:

		return frappe.db.exists(
			"Has Role", {"parent": frappe.session.user, "role": "Healthcare Administrator"}
		)
	"""
	return True
