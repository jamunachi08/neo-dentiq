/**
 * Neo Dentiq odontogram.
 *
 * Each tooth is drawn as five clickable SVG surfaces — mesial, distal, buccal,
 * lingual and occlusal — so charting happens at the surface level, the way
 * clinicians record it. Colour comes from Neo Dentiq Theme, so a practice can
 * recolour the whole chart, switch a condition off, or turn colour coding off
 * entirely without touching code. Colour-blind safe mode adds a letter code to
 * every treated surface so condition is never signalled by colour alone.
 */
frappe.provide("neo_dentiq.odontogram");

const FALLBACK_CONDITION = {
	Sound: "#FFFFFF", Caries: "#DC2626", Restored: "#2563EB",
	"Root Canal Treated": "#D97706", Crowned: "#7C3AED", Veneered: "#0891B2",
	Fractured: "#BE123C", Abraded: "#A16207", Discoloured: "#78716C",
	Mobile: "#EA580C", Watch: "#CA8A04",
};

const FALLBACK_STATUS = {
	Present: {}, Missing: { opacity: 0.25, cross: true },
	Extracted: { opacity: 0.25, cross: true },
	Unerupted: { opacity: 0.4, dashed: true },
	Impacted: { opacity: 0.6, dashed: true },
	Implant: { badge: "I" }, Pontic: { badge: "P" },
	"Primary Retained": { badge: "p" },
};

function conditionColour(condition) {
	if (!neo_dentiq.theme.enabled("colour_coded_odontogram")) return "#FFFFFF";
	return neo_dentiq.theme.colour("tooth_condition", condition,
		FALLBACK_CONDITION[condition] || "#FFFFFF");
}

function conditionGlyph(condition) {
	const entry = neo_dentiq.theme.entry("tooth_condition", condition);
	return (entry && entry.icon) || "";
}

function statusMeta(status) {
	const base = FALLBACK_STATUS[status] || {};
	const entry = neo_dentiq.theme.entry("tooth_status", status);
	return {
		opacity: base.opacity || 1,
		cross: base.cross,
		dashed: base.dashed,
		badge: (entry && entry.icon) || base.badge,
		colour: entry ? entry.colour : null,
		text: entry ? entry.text : "#0F172A",
	};
}

class Odontogram {
	constructor(opts) {
		Object.assign(this, opts);
		this.render();
	}

	async render() {
		this.data = await frappe.call({
			method: "neo_dentiq.api.chart.get_odontogram",
			args: { patient: this.patient, numbering: this.numbering },
		}).then((r) => r.message);

		this.wrapper.empty();
		this.wrapper.append(this.toolbar());
		this.wrapper.append(this.svg());
		this.wrapper.append(this.legend());
		this.wrapper.append(this.detail_panel());
		this.bind();
	}

	toolbar() {
		const i = this.data.indices;
		return $(`
			<div class="ndq-odontogram-toolbar">
				<div class="ndq-indices">
					<span>${__("DMFT")} <b>${i.dmft || 0}</b></span>
					<span>${__("Decayed")} <b>${i.decayed || 0}</b></span>
					<span>${__("Missing")} <b>${i.missing || 0}</b></span>
					<span>${__("Filled")} <b>${i.filled || 0}</b></span>
				</div>
				<div class="ndq-numbering">
					<select class="form-control input-xs" data-numbering>
						${["FDI", "Universal", "Palmer"].map((n) =>
							`<option value="${n}" ${n === this.data.numbering ? "selected" : ""}>${n}</option>`
						).join("")}
					</select>
				</div>
			</div>
		`);
	}

	svg() {
		const arrange = (arr) => {
			const right = arr.filter((t) => t.side === "Right")
				.sort((a, b) => b.tooth_code.localeCompare(a.tooth_code));
			const left = arr.filter((t) => t.side === "Left")
				.sort((a, b) => a.tooth_code.localeCompare(b.tooth_code));
			return { right, left, all: right.concat(left) };
		};
		const upper = arrange(this.data.teeth.filter((t) => t.arch === "Upper"));
		const lower = arrange(this.data.teeth.filter((t) => t.arch === "Lower"));
		const cell = 44;
		const columns = Math.max(upper.all.length, lower.all.length);
		const width = columns * cell + 20;
		const midX = 10 + upper.right.length * cell;

		let body = `<line class="ndq-midline" x1="${midX}" y1="12" x2="${midX}" y2="208"/>`;
		body += `<text class="ndq-quadrant-label" x="${midX / 2}" y="14"
			text-anchor="middle">${__("UPPER RIGHT")}</text>`;
		body += `<text class="ndq-quadrant-label" x="${midX + (width - midX) / 2}" y="14"
			text-anchor="middle">${__("UPPER LEFT")}</text>`;
		body += `<text class="ndq-quadrant-label" x="${midX / 2}" y="206"
			text-anchor="middle">${__("LOWER RIGHT")}</text>`;
		body += `<text class="ndq-quadrant-label" x="${midX + (width - midX) / 2}" y="206"
			text-anchor="middle">${__("LOWER LEFT")}</text>`;

		[upper.all, lower.all].forEach((row, rowIndex) => {
			const y = rowIndex === 0 ? 28 : 128;
			row.forEach((tooth, i) => {
				body += this.tooth_svg(tooth, 10 + i * cell, y, rowIndex === 0);
			});
		});

		return $(`<div class="ndq-odontogram-scroll">
			<svg viewBox="0 0 ${width} 220" class="ndq-odontogram" role="img"
			     aria-label="${__("Tooth chart")}">${body}</svg>
		</div>`);
	}

	tooth_svg(tooth, x, y, upper) {
		const size = 34;
		const third = size / 3;
		const colour = conditionColour(tooth.condition);
		const glyph = conditionGlyph(tooth.condition);
		const meta = statusMeta(tooth.status);
		const dash = meta.dashed ? 'stroke-dasharray="3 2"' : "";
		const treated = (tooth.treated_surfaces || "").toUpperCase();
		const base = "var(--ndq-surface, #fff)";
		const fillFor = (key) => (treated.includes(key) ? colour : base);

		const surfaces = `
			<polygon data-surface="B" points="${x},${y} ${x + size},${y} ${x + size - third},${y + third} ${x + third},${y + third}"
				fill="${fillFor("B")}" stroke="var(--ndq-border, #cbd5e1)" ${dash}/>
			<polygon data-surface="L" points="${x},${y + size} ${x + size},${y + size} ${x + size - third},${y + size - third} ${x + third},${y + size - third}"
				fill="${fillFor("L")}" stroke="var(--ndq-border, #cbd5e1)" ${dash}/>
			<polygon data-surface="M" points="${x},${y} ${x + third},${y + third} ${x + third},${y + size - third} ${x},${y + size}"
				fill="${fillFor("M")}" stroke="var(--ndq-border, #cbd5e1)" ${dash}/>
			<polygon data-surface="D" points="${x + size},${y} ${x + size - third},${y + third} ${x + size - third},${y + size - third} ${x + size},${y + size}"
				fill="${fillFor("D")}" stroke="var(--ndq-border, #cbd5e1)" ${dash}/>
			<rect data-surface="O" x="${x + third}" y="${y + third}" width="${third}" height="${third}"
				fill="${treated.includes("O") || treated.includes("I") ? colour : base}"
				stroke="var(--ndq-border, #cbd5e1)" ${dash}/>
		`;

		const cross = meta.cross
			? `<line x1="${x + 4}" y1="${y + 4}" x2="${x + size - 4}" y2="${y + size - 4}"
				stroke="var(--ndq-muted, #94a3b8)" stroke-width="2"/>
			   <line x1="${x + size - 4}" y1="${y + 4}" x2="${x + 4}" y2="${y + size - 4}"
				stroke="var(--ndq-muted, #94a3b8)" stroke-width="2"/>`
			: "";

		const badge = meta.badge
			? `<circle cx="${x + size / 2}" cy="${y + size / 2}" r="9"
					fill="${meta.colour || "var(--ndq-primary)"}"/>
			   <text x="${x + size / 2}" y="${y + size / 2 + 4}" text-anchor="middle"
					class="ndq-tooth-badge" fill="${meta.text || "#fff"}">${meta.badge}</text>`
			: "";

		// Colour-blind safe mode prints the condition letter on treated teeth
		const code = glyph && treated
			? `<text x="${x + size / 2}" y="${y + size / 2 + 3}" text-anchor="middle"
					class="ndq-tooth-code" fill="#fff">${glyph}</text>`
			: "";

		const planned = this.data.planned.find((p) => p.tooth === tooth.name);
		const plannedRing = planned
			? `<rect x="${x - 3}" y="${y - 3}" width="${size + 6}" height="${size + 6}"
					rx="4" fill="none" stroke="var(--ndq-success, #16a34a)"
					stroke-width="1.5" stroke-dasharray="3 2"/>`
			: "";

		const labelY = upper ? y - 7 : y + size + 15;

		return `<g class="ndq-tooth" data-tooth="${tooth.name}" opacity="${meta.opacity}"
		           tabindex="0" role="button"
		           aria-label="${tooth.tooth_name}, ${tooth.condition}, ${tooth.status}">
			${plannedRing}${surfaces}${cross}${badge}${code}
			<text x="${x + size / 2}" y="${labelY}" text-anchor="middle"
			      class="ndq-tooth-label">${tooth.label}</text>
		</g>`;
	}

	legend() {
		const theme = neo_dentiq.theme.current;
		const map = (theme && theme.enabled && theme.maps && theme.maps.tooth_condition) || null;
		const entries = map
			? Object.entries(map).map(([key, v]) => [v.label || key, v.colour])
			: Object.entries(FALLBACK_CONDITION);
		const items = entries
			.map(([label, colour]) =>
				`<span class="ndq-legend-item"><i style="background:${colour}"></i>${label}</span>`)
			.join("");
		return $(`<div class="ndq-legend">${items}
			<span class="ndq-legend-item"><i class="ndq-planned"></i>${__("Planned")}</span></div>`);
	}

	detail_panel() {
		return $(`<div class="ndq-tooth-detail">
			${__("Click a surface to chart it. Double-click a tooth for its history.")}
		</div>`);
	}

	bind() {
		const me = this;

		this.wrapper.find("[data-numbering]").on("change", function () {
			me.numbering = $(this).val();
			me.render();
		});

		this.wrapper.find(".ndq-tooth").on("click", function (e) {
			me.open_tooth($(this).data("tooth"), $(e.target).data("surface"));
		});

		this.wrapper.find(".ndq-tooth").on("dblclick", function () {
			me.show_history($(this).data("tooth"));
		});

		this.wrapper.find(".ndq-tooth").on("keydown", function (e) {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				me.open_tooth($(this).data("tooth"));
			}
		});
	}

	open_tooth(tooth, surface) {
		const record = this.data.teeth.find((t) => t.name === tooth);
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: `${record.tooth_name} (${record.label})`,
			fields: [
				{ fieldname: "status", label: __("Status"), fieldtype: "Select",
				  options: Object.keys(FALLBACK_STATUS).join("\n"), default: record.status },
				{ fieldname: "condition", label: __("Condition"), fieldtype: "Select",
				  options: Object.keys(FALLBACK_CONDITION).join("\n"),
				  default: record.condition },
				{ fieldtype: "Column Break" },
				{ fieldname: "surfaces", label: __("Surfaces"), fieldtype: "Data",
				  default: surface
					? _.uniq((record.treated_surfaces || "").split("").concat([surface])).join("")
					: record.treated_surfaces,
				  description: __("Any of M D B L O I") },
				{ fieldname: "mobility_grade", label: __("Mobility"), fieldtype: "Select",
				  options: "0\n1\n2\n3", default: record.mobility || "0" },
				{ fieldtype: "Section Break" },
				{ fieldname: "note", label: __("Note"), fieldtype: "Small Text",
				  default: record.note },
			],
			primary_action_label: __("Save tooth"),
			primary_action(values) {
				frappe.call({
					method: "neo_dentiq.api.chart.update_tooth",
					args: Object.assign({ patient: me.patient, tooth }, values),
					callback() {
						dialog.hide();
						frappe.show_alert({ message: __("Tooth updated"), indicator: "green" });
						me.render();
					},
				});
			},
			secondary_action_label: __("Plan treatment here"),
			secondary_action() {
				dialog.hide();
				me.plan_for_tooth(tooth);
			},
		});
		dialog.show();
	}

	plan_for_tooth(tooth) {
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: __("Plan treatment"),
			fields: [
				{ fieldname: "procedure", label: __("Procedure"), fieldtype: "Link",
				  options: "Dental Procedure", reqd: 1 },
				{ fieldname: "practitioner", label: __("Practitioner"), fieldtype: "Link",
				  options: "Dental Practitioner", reqd: 1 },
			],
			primary_action_label: __("Build plan"),
			primary_action(values) {
				frappe.call({
					method: "neo_dentiq.api.clinical.build_plan_from_pathway",
					args: {
						patient: me.patient, practitioner: values.practitioner,
						procedure: values.procedure, tooth,
					},
					callback(r) {
						dialog.hide();
						if (r.message) frappe.set_route("Form", "Treatment Plan", r.message);
					},
					error() {
						dialog.hide();
						frappe.new_doc("Treatment Plan", {
							patient: me.patient, practitioner: values.practitioner,
						});
					},
				});
			},
		});
		dialog.show();
	}

	show_history(tooth) {
		const events = this.data.history.filter((h) => h.tooth === tooth);
		const planned = this.data.planned.filter((p) => p.tooth === tooth);
		const body = events.length || planned.length
			? `
				${planned.length ? `<h6>${__("Planned")}</h6><ul>${planned
					.map((p) => `<li>${p.procedure} — ${p.phase} (${p.status})</li>`)
					.join("")}</ul>` : ""}
				${events.length ? `<h6>${__("History")}</h6><ul>${events
					.map((e) => `<li>${frappe.datetime.str_to_user(e.procedure_date)} — ${e.procedure}
						${e.surfaces ? `(${e.surfaces})` : ""} · ${e.practitioner}</li>`)
					.join("")}</ul>` : ""}
			`
			: `<p class="text-muted">${__("Nothing recorded for this tooth yet.")}</p>`;
		frappe.msgprint({ title: __("Tooth history"), message: body, wide: true });
	}
}

neo_dentiq.odontogram.render = function (wrapper, patient, numbering) {
	return new Odontogram({ wrapper: $(wrapper), patient, numbering });
};
