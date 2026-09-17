frappe.ui.form.on("Sterilization Cycle", {
	refresh(frm) {
		if (frm.doc.cycle_result === "Fail") {
			frm.dashboard.set_headline(
				`<span class="text-danger">${__("Failed cycle. Every tray in this load is quarantined and affected patients are traced.")}</span>`);
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Trace patients"), () => {
				frappe.call({
					method: "neo_dentiq.utils.traceability.trace_cycle",
					args: { cycle: frm.doc.name },
					callback(r) {
						const rows = (r.message || []).map((p) =>
							`<tr><td>${p.patient_name}</td><td>${p.procedure_date}</td>
							<td>${p.instrument_tray}</td></tr>`).join("");
						frappe.msgprint({
							title: __("Patients treated with this load"), wide: true,
							message: rows
								? `<table class="table table-bordered"><thead><tr>
									<th>${__("Patient")}</th><th>${__("Date")}</th>
									<th>${__("Tray")}</th></tr></thead>
									<tbody>${rows}</tbody></table>`
								: __("No patient procedures have used this load yet."),
						});
					},
				});
			});
		}
		frm.add_custom_button(__("Load dirty trays"), () => {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Instrument Tray",
					filters: { status: "Dirty / Awaiting Reprocessing",
					           clinic: frm.doc.clinic || undefined },
					fields: ["name", "instrument_kit"], limit_page_length: 40,
				},
				callback(r) {
					(r.message || []).forEach((t) => {
						frm.add_child("trays", { instrument_tray: t.name, result: "Pass" });
					});
					frm.refresh_field("trays");
				},
			});
		});
	},
});
