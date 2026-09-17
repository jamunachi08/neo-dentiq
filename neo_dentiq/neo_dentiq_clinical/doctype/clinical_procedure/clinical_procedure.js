frappe.ui.form.on("Clinical Procedure", {
	refresh(frm) {
		neo_dentiq.banner.render(frm);

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Scan tray"), () => {
				frappe.prompt(
					{ fieldname: "tray_code", label: __("Tray barcode"), fieldtype: "Data",
					  reqd: 1 },
					(v) => {
						frappe.call({
							method: "neo_dentiq.api.clinical.scan_tray",
							args: { tray_code: v.tray_code },
							callback(r) {
								const t = r.message;
								if (!t.usable) {
									frappe.msgprint({
										title: __("Tray cannot be used"),
										message: t.reason, indicator: "red",
									});
									return;
								}
								frm.add_child("trays_used", { instrument_tray: t.name });
								frm.refresh_field("trays_used");
								frappe.show_alert({
									message: __("Tray {0} added", [t.name]),
									indicator: "green" });
							},
						});
					}, __("Instrument traceability"), __("Add tray"));
			});

			frm.add_custom_button(__("Pull default consumables"), () => {
				frm.clear_table("consumables");
				frm.call("pull_default_consumables").then(() =>
					frm.refresh_field("consumables"));
			});
		}

		if (frm.doc.docstatus === 1 && frm.doc.stock_entry) {
			frm.add_custom_button(__("Stock entry"), () =>
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry), __("View"));
		}
	},

	procedure(frm) {
		if (!frm.doc.procedure) return;
		frappe.db.get_value("Dental Procedure", frm.doc.procedure,
			["requires_consent", "instrument_kit", "default_duration"]).then((r) => {
			const d = r.message || {};
			if (d.requires_consent && !frm.doc.consent_record) {
				frm.dashboard.set_headline(
					`<span class="text-warning">${__("This procedure needs a signed consent form before it can be submitted.")}</span>`);
			}
			if (d.instrument_kit) {
				frappe.call({
					method: "neo_dentiq.api.clinical.available_trays",
					args: { instrument_kit: d.instrument_kit, clinic: frm.doc.clinic },
					callback(res) {
						const trays = res.message || [];
						if (!trays.length) {
							frappe.msgprint({
								title: __("No sterile trays"),
								message: __("No sterile {0} tray is available. Reprocess one before this procedure.",
									[d.instrument_kit]),
								indicator: "red",
							});
						}
					},
				});
			}
		});
	},
});
