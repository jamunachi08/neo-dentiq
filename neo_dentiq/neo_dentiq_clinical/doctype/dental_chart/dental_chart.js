frappe.ui.form.on("Dental Chart", {
	refresh(frm) {
		if (!frm.doc.patient) return;
		neo_dentiq.odontogram.render(
			frm.get_field("odontogram_html").$wrapper, frm.doc.patient,
			frm.doc.numbering_system);

		frm.add_custom_button(__("Clinical passport"), () => {
			frappe.set_route("query-report", "Patient Clinical Passport",
				{ patient: frm.doc.patient });
		});
		frm.add_custom_button(__("Perio chart"), () => {
			frappe.new_doc("Periodontal Chart", { patient: frm.doc.patient });
		});
	},
	numbering_system(frm) {
		frm.save().then(() => frm.refresh());
	},
});
