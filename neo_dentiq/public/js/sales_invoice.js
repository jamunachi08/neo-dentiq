frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (!frm.doc.neo_dentiq_patient) return;
		frm.add_custom_button(__("Patient record"), () =>
			frappe.set_route("Form", "Patient", frm.doc.neo_dentiq_patient), __("Neo Dentiq"));
		if (frm.doc.neo_dentiq_zatca_qr) {
			frm.dashboard.add_comment(__("ZATCA e-invoice QR generated."), "blue", true);
		}
	},
});
