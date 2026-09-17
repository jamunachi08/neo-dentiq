frappe.ui.form.on("Dental Appointment", {
	refresh(frm) {
		neo_dentiq.banner.render(frm);

		if (frm.doc.no_show_risk >= 60) {
			frm.dashboard.set_headline(
				`<span class="text-danger">${__("High no-show risk")}: ${frm.doc.no_show_risk}%
				— ${frm.doc.risk_factors || ""}</span>`);
		}

		if (frm.is_new()) return;

		if (["Scheduled", "Confirmed", "Requested"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Mark arrived"), () => frm.set_value("status", "Arrived")
				.then(() => frm.save()));
			frm.add_custom_button(__("Send reminder"), () => {
				frm.call("send_reminder").then(() => frm.reload_doc());
			});
		}
		if (frm.doc.status === "Arrived") {
			frm.add_custom_button(__("Seat in operatory"),
				() => frm.set_value("status", "In Operatory").then(() => frm.save()));
		}
		if (["In Operatory", "In Progress"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Clinical note"), () => {
				frm.call("create_clinical_note").then((r) => {
					if (r.message) frappe.set_route("Form", "Clinical Note", r.message);
				});
			});
		}
		if (frm.doc.status === "Completed" && !frm.doc.sales_invoice) {
			frm.add_custom_button(__("Create invoice"), () => {
				frm.call("create_invoice").then((r) => {
					if (r.message) frappe.set_route("Form", "Sales Invoice", r.message);
				});
			});
		}

		frm.add_custom_button(__("Find next open slot"), () => {
			frappe.call({
				method: "neo_dentiq.utils.scheduling.find_next_available",
				args: {
					clinic: frm.doc.clinic, appointment_type: frm.doc.appointment_type,
					duration: frm.doc.duration, practitioner: frm.doc.practitioner,
				},
				callback(r) {
					const rows = (r.message || []).slice(0, 15).map((s) =>
						`<tr><td>${s.date}</td><td>${s.display}</td>
						<td>${s.practitioner}</td><td>${s.operatory || ""}</td></tr>`).join("");
					frappe.msgprint({
						title: __("Next available"), wide: true,
						message: rows
							? `<table class="table table-bordered"><thead><tr>
								<th>${__("Date")}</th><th>${__("Time")}</th>
								<th>${__("Practitioner")}</th><th>${__("Operatory")}</th>
								</tr></thead><tbody>${rows}</tbody></table>`
							: __("No open slots in the next two weeks."),
					});
				},
			});
		}, __("Scheduling"));
	},

	practitioner(frm) { frm.trigger("show_slots"); },
	appointment_date(frm) { frm.trigger("show_slots"); },

	show_slots(frm) {
		if (!(frm.doc.practitioner && frm.doc.appointment_date)) return;
		frappe.call({
			method: "neo_dentiq.utils.scheduling.available_slots",
			args: {
				practitioner: frm.doc.practitioner, date: frm.doc.appointment_date,
				duration: frm.doc.duration, appointment_type: frm.doc.appointment_type,
			},
			callback(r) {
				const slots = r.message || [];
				if (!slots.length) {
					frm.dashboard.clear_headline();
					frm.dashboard.set_headline(
						__("No open slots that day. Try another date or practitioner."));
					return;
				}
				const buttons = slots.slice(0, 40).map((s) =>
					`<button type="button" class="btn btn-xs btn-default ndq-slot-btn"
						data-time="${s.time}" style="margin:2px">${s.display}</button>`).join("");
				frm.dashboard.clear_headline();
				frm.dashboard.set_headline(
					`<div>${__("Open slots")}: ${buttons}</div>`);
				frm.dashboard.$headline.find(".ndq-slot-btn").on("click", function () {
					frm.set_value("appointment_time", $(this).data("time"));
				});
			},
		});
	},
});
