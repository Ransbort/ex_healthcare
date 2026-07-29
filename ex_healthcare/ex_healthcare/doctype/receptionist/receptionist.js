// Copyright (c) 2026, Pep Sports Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Receptionist", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Active") {
			frm.add_custom_button(__("Open Cashier Portal"), () => {
				frappe.set_route("cashier-portal");
			});
		}
	},

	user(frm) {
		if (frm.doc.user && !frm.doc.employee) {
			frappe.db.get_value("Employee", { user_id: frm.doc.user }, "name", (r) => {
				if (r && r.name) {
					frm.set_value("employee", r.name);
				}
			});
		}
	},
});
