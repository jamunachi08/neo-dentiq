frappe.ui.form.on("Periodontal Chart", {
	refresh(frm) {
		if (!frm.is_new()) {
			neo_dentiq.perio.render(frm.get_field("perio_chart_html").$wrapper, frm);
		}
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Build full mouth"), () => {
				frm.call("build_full_mouth").then(() => frm.refresh());
			});
		}
		frm.add_custom_button(__("Compare with previous"), () => {
			frappe.call({
				method: "neo_dentiq.api.chart.compare_charts",
				args: { patient: frm.doc.patient },
				callback(r) {
					const rows = (r.message || []).map((c) => `
						<tr><td>${frappe.datetime.str_to_user(c.exam_date)}</td>
						<td>${c.perio_stage || ""} ${c.perio_grade || ""}</td>
						<td>${c.bop_percent}%</td><td>${c.mean_pd}</td>
						<td>${c.sites_5mm_plus}</td></tr>`).join("");
					frappe.msgprint({
						title: __("Periodontal trend"), wide: true,
						message: `<table class="table table-bordered">
							<thead><tr><th>${__("Date")}</th><th>${__("Diagnosis")}</th>
							<th>${__("BOP")}</th><th>${__("Mean PD")}</th>
							<th>${__("Sites ≥5mm")}</th></tr></thead>
							<tbody>${rows}</tbody></table>`,
					});
				},
			});
		});
	},
	patient(frm) {
		neo_dentiq.banner.render(frm);
	},
});
