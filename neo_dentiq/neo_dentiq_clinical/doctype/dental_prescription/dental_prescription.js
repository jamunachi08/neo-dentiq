frappe.ui.form.on("Dental Prescription", {
	refresh(frm) {
		neo_dentiq.banner.render(frm);
		frm.add_custom_button(__("Run safety check"), () => {
			frm.call("check_safety").then((r) => {
				const result = r.message || {};
				frm.get_field("safety_html").$wrapper.html(
					(result.messages || []).length
						? `<div class="ndq-banner">${result.messages.join("<br>")}</div>`
						: `<div class="text-success">${__("No interactions, allergies or duplications found.")}</div>`);
			});
		});
	},
	items_add(frm) { frm.trigger("refresh"); },
});
