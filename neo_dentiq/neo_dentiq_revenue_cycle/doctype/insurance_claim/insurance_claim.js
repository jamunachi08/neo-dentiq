frappe.ui.form.on("Insurance Claim", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__("Generate payer payload"), () => {
			frm.call("generate_payload").then((r) => {
				frappe.msgprint({
					title: __("{0} payload", [r.message.mode]), wide: true,
					message: `<pre style="max-height:420px;overflow:auto">${
						frappe.utils.escape_html(r.message.payload)}</pre>`,
				});
			});
		}, __("Payer"));

		frm.add_custom_button(__("Mark submitted"), () => {
			frappe.prompt(
				{ fieldname: "reference", label: __("Transmission reference"),
				  fieldtype: "Data" },
				(v) => frm.call("mark_submitted", v).then(() => frm.reload_doc()),
				__("Submit to payer"), __("Confirm"));
		}, __("Payer"));

		if (frm.doc.total_paid) {
			frm.add_custom_button(__("Post payer payment"), () => {
				frm.call("post_payment").then((r) => {
					if (r.message) frappe.set_route("Form", "Payment Entry", r.message);
				});
			}, __("Payer"));
		}

		if (frm.doc.status === "Denied") {
			frm.add_custom_button(__("Create appeal"), () => {
				frm.call("create_appeal").then((r) => {
					if (r.message) frappe.set_route("Form", "Insurance Claim", r.message);
				});
			}, __("Payer"));
		}

		if (frm.doc.aging_days > 45) {
			frm.dashboard.set_headline(
				`<span class="text-danger">${__("Aged {0} days without settlement.",
					[frm.doc.aging_days])}</span>`);
		}
	},
});
