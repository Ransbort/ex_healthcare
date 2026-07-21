frappe.ui.form.on("Ex Healthcare Settings", {
	refresh: function (frm) {
		frm.get_field("healthcare_settings_link_html").html(`
			<div class="alert alert-info" style="margin-top: 8px;">
				These values are mirrored from
				<a href="#" onclick="frappe.set_route('Form', 'Healthcare Settings'); return false;">
					Healthcare Settings
				</a>
				and are read-only here. To change them, open Healthcare Settings directly.
			</div>
		`);
	},
});
