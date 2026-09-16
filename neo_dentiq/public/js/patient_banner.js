/** Medical-alert banner shown at the top of every clinical document. */
frappe.provide("neo_dentiq.banner");

neo_dentiq.banner.render = function (frm, patient_field) {
	const patient = frm.doc[patient_field || "patient"];
	const field = frm.get_field("medical_alert_html") || frm.get_field("safety_html");
	if (!patient || !field) return;

	frappe.call({
		method: "neo_dentiq.api.clinical.patient_summary",
		args: { patient },
		callback(r) {
			const data = r.message;
			if (!data) return;
			const alerts = (data.alerts || []).map((a) => {
				const critical = /ALLERGY|PREGNANT|Critical/i.test(a);
				return `<span class="ndq-alert ${critical ? "critical" : ""}">${a}</span>`;
			}).join("");

			const prophylaxis = data.prophylaxis && data.prophylaxis.required
				? `<div class="ndq-prophylaxis">
					${__("Antibiotic prophylaxis indicated")}: ${data.prophylaxis.regimen}
				   </div>`
				: "";

			const chips = `
				<span class="ndq-chip">${__("Caries risk")}: ${data.caries_risk}</span>
				<span class="ndq-chip">${__("Perio risk")}: ${data.perio_risk}</span>
				<span class="ndq-chip">${__("No-show")}: ${data.no_show_score || 0}%</span>
				${data.balance ? `<span class="ndq-chip warn">${__("Balance")}:
					${format_currency(data.balance)}</span>` : ""}
			`;

			field.$wrapper.html(`
				<div class="ndq-banner">
					<div class="ndq-banner-head">
						<strong>${data.patient_name}</strong>
						<span class="text-muted">${data.age || ""} · ${data.sex || ""}</span>
					</div>
					${alerts ? `<div class="ndq-alerts">${alerts}</div>` : ""}
					${prophylaxis}
					<div class="ndq-chips">${chips}</div>
				</div>
			`);
		},
	});
};
