/**
 * Six-point periodontal charting grid.
 *
 * Probing depths are entered per site with the keyboard: type a depth, the
 * cursor advances. Sites at or above 4 mm colour amber, 6 mm and above red,
 * so a clinician reads disease distribution without reading numbers.
 */
frappe.provide("neo_dentiq.perio");

const PD_FIELDS = ["pd_db", "pd_b", "pd_mb", "pd_dl", "pd_l", "pd_ml"];
const BOP_FIELDS = ["bop_db", "bop_b", "bop_mb", "bop_dl", "bop_l", "bop_ml"];

class PerioGrid {
	constructor({ wrapper, frm }) {
		this.wrapper = $(wrapper);
		this.frm = frm;
		this.render();
	}

	render() {
		const rows = this.frm.doc.readings || [];
		if (!rows.length) {
			this.wrapper.html(`<div class="text-muted">
				${__("Use 'Build Full Mouth' to lay out all 32 teeth, then probe.")}</div>`);
			return;
		}
		const upper = rows.filter((r) => String(r.tooth).charAt(0) <= "2");
		const lower = rows.filter((r) => String(r.tooth).charAt(0) > "2");
		this.wrapper.html(`
			<div class="ndq-perio">
				${this.section(__("Maxillary"), upper)}
				${this.section(__("Mandibular"), lower)}
				<div class="ndq-perio-summary"></div>
			</div>
		`);
		this.bind();
		this.summarise();
	}

	section(title, rows) {
		const head = rows.map((r) =>
			`<th title="${r.tooth}">${r.tooth}</th>`).join("");
		const buccal = rows.map((r) => this.site_cells(r, ["pd_db", "pd_b", "pd_mb"],
			["bop_db", "bop_b", "bop_mb"])).join("");
		const lingual = rows.map((r) => this.site_cells(r, ["pd_dl", "pd_l", "pd_ml"],
			["bop_dl", "bop_l", "bop_ml"])).join("");
		const recession = rows.map((r) =>
			`<td colspan="3"><input class="ndq-perio-input" type="number" min="0" max="15"
				data-row="${r.name}" data-field="rec_b" value="${r.rec_b || 0}"></td>`).join("");
		const mobility = rows.map((r) =>
			`<td colspan="3"><select class="ndq-perio-select" data-row="${r.name}"
				data-field="mobility">${[0, 1, 2, 3].map((n) =>
					`<option ${String(r.mobility) === String(n) ? "selected" : ""}>${n}</option>`)
					.join("")}</select></td>`).join("");

		return `
			<div class="ndq-perio-arch">
				<h6>${title}</h6>
				<div class="ndq-perio-scroll">
				<table class="ndq-perio-table">
					<thead><tr><th class="sticky">${__("Tooth")}</th>${head}</tr></thead>
					<tbody>
						<tr><th class="sticky">${__("Buccal PD")}</th>${buccal}</tr>
						<tr><th class="sticky">${__("Lingual PD")}</th>${lingual}</tr>
						<tr><th class="sticky">${__("Recession")}</th>${recession}</tr>
						<tr><th class="sticky">${__("Mobility")}</th>${mobility}</tr>
					</tbody>
				</table>
				</div>
			</div>`;
	}

	site_cells(row, pdFields, bopFields) {
		return pdFields.map((field, i) => {
			const value = row[field] || 0;
			const cls = value >= 6 ? "deep" : value >= 4 ? "moderate" : "";
			const bop = row[bopFields[i]] ? "bleeding" : "";
			return `<td class="ndq-perio-site ${cls} ${bop}">
				<input class="ndq-perio-input" type="number" min="0" max="15"
					data-row="${row.name}" data-field="${field}"
					data-bop="${bopFields[i]}" value="${value}">
			</td>`;
		}).join("");
	}

	bind() {
		const me = this;
		this.wrapper.on("change", ".ndq-perio-input, .ndq-perio-select", function () {
			const $el = $(this);
			const row = me.frm.doc.readings.find((r) => r.name === $el.data("row"));
			if (!row) return;
			frappe.model.set_value(row.doctype, row.name, $el.data("field"), $el.val());
			me.recolour($el);
			me.summarise();
		});

		// Right-click a site toggles bleeding on probing
		this.wrapper.on("contextmenu", ".ndq-perio-site", function (e) {
			e.preventDefault();
			const $input = $(this).find("input");
			const row = me.frm.doc.readings.find((r) => r.name === $input.data("row"));
			const field = $input.data("bop");
			if (!row || !field) return;
			frappe.model.set_value(row.doctype, row.name, field, row[field] ? 0 : 1);
			$(this).toggleClass("bleeding");
			me.summarise();
		});

		// Typing a depth moves to the next site
		this.wrapper.on("keyup", ".ndq-perio-input", function (e) {
			if (e.key === "Enter" || $(this).val().length >= 2) {
				const inputs = me.wrapper.find(".ndq-perio-input");
				const next = inputs.index(this) + 1;
				if (inputs[next]) inputs[next].focus();
			}
		});
	}

	recolour($el) {
		const value = parseInt($el.val() || 0, 10);
		const $cell = $el.closest(".ndq-perio-site");
		$cell.removeClass("deep moderate");
		if (value >= 6) $cell.addClass("deep");
		else if (value >= 4) $cell.addClass("moderate");
	}

	summarise() {
		let sites = 0, bleeding = 0, deep = 0, sum = 0;
		(this.frm.doc.readings || []).forEach((row) => {
			if (row.is_missing) return;
			PD_FIELDS.forEach((f) => {
				sites += 1;
				const v = parseInt(row[f] || 0, 10);
				sum += v;
				if (v >= 5) deep += 1;
			});
			BOP_FIELDS.forEach((f) => { if (row[f]) bleeding += 1; });
		});
		const bop = sites ? ((bleeding * 100) / sites).toFixed(1) : 0;
		const mean = sites ? (sum / sites).toFixed(2) : 0;
		this.wrapper.find(".ndq-perio-summary").html(`
			<span>${__("BOP")} <b>${bop}%</b></span>
			<span>${__("Mean PD")} <b>${mean} mm</b></span>
			<span>${__("Sites ≥5mm")} <b>${deep}</b></span>
			<span class="text-muted">${__("Right-click a site to mark bleeding")}</span>
		`);
	}
}

neo_dentiq.perio.render = function (wrapper, frm) {
	return new PerioGrid({ wrapper, frm });
};
