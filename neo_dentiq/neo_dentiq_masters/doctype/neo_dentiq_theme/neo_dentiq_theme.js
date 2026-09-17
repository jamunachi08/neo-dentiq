frappe.ui.form.on("Neo Dentiq Theme", {
	refresh(frm) {
		frm.trigger("draw_preview");

		frm.add_custom_button(__("Apply theme now"), () => {
			frm.save().then(() => {
				frappe.call({ method: "neo_dentiq.neo_dentiq_masters.doctype.neo_dentiq_theme.neo_dentiq_theme.get_theme" })
					.then((r) => {
						neo_dentiq.theme.apply(r.message);
						frappe.show_alert({ message: __("Theme applied"), indicator: "green" });
					});
			});
		});

		frm.add_custom_button(__("Restore default colours"), () => {
			frappe.confirm(
				__("Reset every colour table to the shipped defaults? Your palette and feature switches are kept."),
				() => frm.call("reset_colour_tables").then(() => frm.reload_doc()));
		});

		if (!frm.doc.enable_theme) {
			frm.dashboard.set_headline(
				__("The theme is off. Neo Dentiq is using the stock Frappe appearance."));
		}
	},

	theme_preset(frm) {
		if (frm.doc.theme_preset === "Custom") return;
		frm.call("preview_preset", { preset: frm.doc.theme_preset }).then((r) => {
			Object.entries(r.message || {}).forEach(([field, colour]) =>
				frm.set_value(field, colour));
			frm.trigger("draw_preview");
		});
	},

	enable_theme(frm) { frm.trigger("draw_preview"); },
	primary_colour(frm) { frm.trigger("mark_custom"); },
	secondary_colour(frm) { frm.trigger("mark_custom"); },
	accent_colour(frm) { frm.trigger("mark_custom"); },

	mark_custom(frm) {
		if (frm.doc.theme_preset !== "Custom") frm.set_value("theme_preset", "Custom");
		frm.trigger("draw_preview");
	},

	draw_preview(frm) {
		const d = frm.doc;
		const wrapper = frm.get_field("preview_html").$wrapper;
		if (!d.enable_theme) {
			wrapper.html(`<div class="text-muted">${__("Enable the theme to see a preview.")}</div>`);
			return;
		}

		const swatch = (label, colour) => `
			<div class="ndq-swatch">
				<span style="background:${colour}"></span>
				<small>${label}<br><code>${colour || ""}</code></small>
			</div>`;

		const pill = (row) => `
			<span class="ndq-preview-pill"
				style="background:${row.colour};color:${row.text_colour || "#fff"}">
				${row.label || row.key}</span>`;

		const conditions = (d.tooth_condition_colours || []).filter((r) => r.is_active);
		const statuses = (d.appointment_status_colours || []).filter((r) => r.is_active);

		wrapper.html(`
			<div class="ndq-preview" style="--p:${d.primary_colour};--s:${d.secondary_colour};
				--a:${d.accent_colour};--bg:${d.background_colour};--sf:${d.surface_colour};
				--tx:${d.text_colour};--bd:${d.border_colour}">

				<div class="ndq-preview-hero">
					<strong>${__("Neo Dentiq")}</strong>
					<span>${d.theme_preset}</span>
				</div>

				<div class="ndq-preview-body">
					<div class="ndq-swatches">
						${swatch(__("Primary"), d.primary_colour)}
						${swatch(__("Secondary"), d.secondary_colour)}
						${swatch(__("Accent"), d.accent_colour)}
						${swatch(__("Success"), d.success_colour)}
						${swatch(__("Warning"), d.warning_colour)}
						${swatch(__("Danger"), d.danger_colour)}
					</div>

					<h6>${__("Appointment statuses")}</h6>
					<div class="ndq-preview-row">${statuses.map(pill).join("")}</div>

					<h6>${__("Tooth conditions")}</h6>
					<div class="ndq-preview-row">${conditions.map(pill).join("")}</div>

					<div class="ndq-preview-card">
						<span class="ndq-preview-dot" style="background:${d.danger_colour}"></span>
						${__("Allergy: Penicillin — anaphylaxis")}
					</div>
				</div>
			</div>
		`);
	},
});
