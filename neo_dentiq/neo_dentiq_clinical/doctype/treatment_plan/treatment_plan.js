frappe.ui.form.on("Treatment Plan", {
	refresh(frm) {
		neo_dentiq.banner.render(frm);
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__("Accept all"), () => {
			frm.call("accept_all").then(() => frm.reload_doc());
		}, __("Case"));

		frm.add_custom_button(__("Payment plan"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Offer a payment plan"),
				fields: [
					{ fieldname: "installments", label: __("Installments"),
					  fieldtype: "Int", default: 6 },
					{ fieldname: "down_payment", label: __("Down payment"),
					  fieldtype: "Currency" },
				],
				primary_action_label: __("Create plan"),
				primary_action(v) {
					frm.call("create_payment_plan", v).then((r) => {
						d.hide();
						if (r.message) frappe.set_route("Form", "Patient Payment Plan",
							r.message);
					});
				},
			});
			d.show();
		}, __("Case"));

		frm.add_custom_button(__("Request pre-authorisation"), () => {
			frm.call("create_preauthorization").then((r) => {
				if (r.message) frappe.set_route("Form", "Insurance Pre Authorization",
					r.message);
			});
		}, __("Case"));

		frm.add_custom_button(__("Schedule next phase"), () => {
			frm.call("schedule_next_phase").then((r) => {
				if (!r.message) {
					frappe.msgprint(__("Nothing accepted is waiting to be scheduled."));
					return;
				}
				frappe.new_doc("Dental Appointment", {
					patient: frm.doc.patient, practitioner: frm.doc.practitioner,
					clinic: frm.doc.clinic, treatment_plan: frm.doc.name,
					duration: r.message.duration,
				});
			});
		}, __("Case"));

		frm.dashboard.add_indicator(
			__("Case acceptance: {0}%", [frm.doc.acceptance_percent || 0]),
			frm.doc.acceptance_percent >= 70 ? "green"
				: frm.doc.acceptance_percent >= 40 ? "orange" : "red");
	},
});
