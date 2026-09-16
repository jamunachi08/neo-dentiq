frappe.ui.form.on("Patient", {
	refresh(frm) {
		if (frm.is_new()) return;
		neo_dentiq.banner.render(frm, "name");

		frm.add_custom_button(__("Odontogram"), () => {
			frappe.db.get_value("Dental Chart", { patient: frm.doc.name }, "name")
				.then((r) => {
					if (r.message && r.message.name) {
						frappe.set_route("Form", "Dental Chart", r.message.name);
					} else {
						frappe.new_doc("Dental Chart", { patient: frm.doc.name });
					}
				});
		}, __("Clinical"));

		frm.add_custom_button(__("Perio chart"), () => {
			frappe.new_doc("Periodontal Chart", { patient: frm.doc.name });
		}, __("Clinical"));

		frm.add_custom_button(__("Treatment plan"), () => {
			frappe.new_doc("Treatment Plan", { patient: frm.doc.name });
		}, __("Clinical"));

		frm.add_custom_button(__("Clinical passport"), () => {
			frappe.set_route("query-report", "Patient Clinical Passport",
				{ patient: frm.doc.name });
		}, __("Clinical"));

		frm.add_custom_button(__("Book appointment"), () => {
			frappe.new_doc("Dental Appointment", { patient: frm.doc.name });
		}, __("Actions"));

		frm.add_custom_button(__("Verify insurance"), () => {
			frappe.call({
				method: "neo_dentiq.utils.insurance.estimate_coverage.verify_eligibility",
				args: { patient: frm.doc.name },
				freeze: true,
				callback(r) {
					frappe.msgprint({
						title: __("Eligibility"),
						message: `<pre>${JSON.stringify(r.message, null, 2)}</pre>`,
					});
					frm.reload_doc();
				},
			});
		}, __("Actions"));

		frm.add_custom_button(__("Radiation dose"), () => {
			frappe.call({
				method: "neo_dentiq.api.clinical.cumulative_dose",
				args: { patient: frm.doc.name },
				callback(r) {
					const d = r.message;
					frappe.msgprint({
						title: __("Cumulative radiation exposure"),
						message: `${__("Lifetime")}: <b>${d.total_msv} mSv</b><br>
							${__("Last 12 months")}: <b>${d.last_12_months_msv} mSv</b><br>
							${__("Repeat rate")}: ${d.repeat_rate}%`,
					});
				},
			});
		}, __("Actions"));
	},

	dob(frm) {
		if (frm.doc.dob) frm.trigger("refresh_age");
	},
});
