/**
 * Neo Dentiq odontogram.
 *
 * Renders an anatomically arranged tooth chart as inline SVG. Each tooth is
 * drawn as five clickable surfaces (mesial, distal, buccal, lingual, occlusal)
 * so charting happens at the surface level, the way clinicians actually record
 * it. Colour encodes clinical condition; it is information, not decoration.
 */
frappe.provide("neo_dentiq.odontogram");

const CONDITION_COLOR = {
	Sound: "var(--fg-color)",
	Caries: "#dc2626",
	Restored: "#2563eb",
	"Root Canal Treated": "#d97706",
	Crowned: "#7c3aed",
	Veneered: "#0891b2",
	Fractured: "#be123c",
	Abraded: "#a16207",
	Discoloured: "#78716c",
	Mobile: "#ea580c",
	Watch: "#ca8a04",
};

const STATUS_STYLE = {
	Present: {},
	Missing: { opacity: 0.25, cross: true },
	Extracted: { opacity: 0.25, cross: true },
	Unerupted: { opacity: 0.4, dashed: true },
	Impacted: { opacity: 0.6, dashed: true },
	Implant: { badge: "I" },
	Pontic: { badge: "P" },
	"Primary Retained": { badge: "p" },
};

const SURFACE_KEYS = ["M", "D", "B", "L", "O"];

class Odontogram {
	constructor(opts) {
		Object.assign(this, opts);
		this.selected = null;
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
					<span>DMFT <b>${i.dmft || 0}</b></span>
					<span>Decayed <b>${i.decayed || 0}</b></span>
					<span>Missing <b>${i.missing || 0}</b></span>
					<span>Filled <b>${i.filled || 0}</b></span>
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
		const upper = this.data.teeth.filter((t) => t.arch === "Upper");
		const lower = this.data.teeth.filter((t) => t.arch === "Lower");
		const order = (arr, reverse) => {
			// Right quadrant runs 8 -> 1, left quadrant runs 1 -> 8
			const right = arr.filter((t) => t.side === "Right")
				.sort((a, b) => b.tooth_code.localeCompare(a.tooth_code));
			const left = arr.filter((t) => t.side === "Left")
				.sort((a, b) => a.tooth_code.localeCompare(b.tooth_code));
			return right.concat(left);
		};
		const rows = [order(upper), order(lower)];
		const cell = 44;
		const width = Math.max(rows[0].length, rows[1].length) * cell + 20;

		let body = "";
		rows.forEach((row, rowIndex) => {
			const y = rowIndex === 0 ? 24 : 130;
			row.forEach((tooth, i) => {
				body += this.tooth_svg(tooth, 10 + i * cell, y, rowIndex === 0);
			});
		});

		return $(`<div class="ndq-odontogram-scroll">
			<svg viewBox="0 0 ${width} 220" class="ndq-odontogram" role="img"
			     aria-label="Tooth chart">${body}</svg>
		</div>`);
	}

	tooth_svg(tooth, x, y, upper) {
		const size = 34;
		const third = size / 3;
		const colour = CONDITION_COLOR[tooth.condition] || "var(--fg-color)";
		const style = STATUS_STYLE[tooth.status] || {};
		const opacity = style.opacity || 1;
		const dash = style.dashed ? 'stroke-dasharray="3 2"' : "";
		const treated = (tooth.treated_surfaces || "").toUpperCase();
		const fillFor = (key) => (treated.includes(key) ? colour : "var(--fg-color)");
		const labelY = upper ? y - 6 : y + size + 14;

		const surfaces = `
			<polygon data-surface="B" points="${x},${y} ${x + size},${y} ${x + size - third},${y + third} ${x + third},${y + third}"
				fill="${fillFor("B")}" stroke="var(--border-color)" ${dash}/>
			<polygon data-surface="L" points="${x},${y + size} ${x + size},${y + size} ${x + size - third},${y + size - third} ${x + third},${y + size - third}"
				fill="${fillFor("L")}" stroke="var(--border-color)" ${dash}/>
			<polygon data-surface="M" points="${x},${y} ${x + third},${y + third} ${x + third},${y + size - third} ${x},${y + size}"
				fill="${fillFor("M")}" stroke="var(--border-color)" ${dash}/>
			<polygon data-surface="D" points="${x + size},${y} ${x + size - third},${y + third} ${x + size - third},${y + size - third} ${x + size},${y + size}"
				fill="${fillFor("D")}" stroke="var(--border-color)" ${dash}/>
			<rect data-surface="O" x="${x + third}" y="${y + third}" width="${third}" height="${third}"
				fill="${fillFor("O") === "var(--fg-color)" && treated.includes("I") ? colour : fillFor("O")}"
				stroke="var(--border-color)" ${dash}/>
		`;

		const cross = style.cross
			? `<line x1="${x}" y1="${y}" x2="${x + size}" y2="${y + size}" stroke="#94a3b8" stroke-width="2"/>
			   <line x1="${x + size}" y1="${y}" x2="${x}" y2="${y + size}" stroke="#94a3b8" stroke-width="2"/>`
			: "";

		const badge = style.badge
			? `<text x="${x + size / 2}" y="${y + size / 2 + 4}" text-anchor="middle"
			         class="ndq-tooth-badge">${style.badge}</text>`
			: "";

		const planned = this.data.planned.find((p) => p.tooth === tooth.name);
		const plannedRing = planned
			? `<rect x="${x - 2}" y="${y - 2}" width="${size + 4}" height="${size + 4}"
			         fill="none" stroke="#16a34a" stroke-width="1.5" stroke-dasharray="3 2"/>`
			: "";

		return `<g class="ndq-tooth" data-tooth="${tooth.name}" opacity="${opacity}"
		           tabindex="0" role="button" aria-label="${tooth.tooth_name}">
			${plannedRing}${surfaces}${cross}${badge}
			<text x="${x + size / 2}" y="${labelY}" text-anchor="middle"
			      class="ndq-tooth-label">${tooth.label}</text>
		</g>`;
	}

	legend() {
		const items = Object.entries(CONDITION_COLOR)
			.map(([label, colour]) =>
				`<span class="ndq-legend-item"><i style="background:${colour}"></i>${label}</span>`)
			.join("");
		return $(`<div class="ndq-legend">${items}
			<span class="ndq-legend-item"><i class="ndq-planned"></i>Planned</span></div>`);
	}

	detail_panel() {
		return $(`<div class="ndq-tooth-detail text-muted">
			Select a tooth to chart its condition, or double-click to see its history.
		</div>`);
	}

	bind() {
		const me = this;

		this.wrapper.find("[data-numbering]").on("change", function () {
			me.numbering = $(this).val();
			me.render();
		});

		this.wrapper.find(".ndq-tooth").on("click", function (e) {
			const tooth = $(this).data("tooth");
			const surface = $(e.target).data("surface");
			me.open_tooth(tooth, surface);
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
				{
					fieldname: "status", label: __("Status"), fieldtype: "Select",
					options: Object.keys(STATUS_STYLE).join("\n"), default: record.status,
				},
				{
					fieldname: "condition", label: __("Condition"), fieldtype: "Select",
					options: Object.keys(CONDITION_COLOR).join("\n"),
					default: record.condition,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "surfaces", label: __("Surfaces"), fieldtype: "Data",
					default: surface
						? _.uniq((record.treated_surfaces || "").split("").concat([surface]))
							.join("")
						: record.treated_surfaces,
					description: __("Any of M D B L O I"),
				},
				{
					fieldname: "mobility_grade", label: __("Mobility"), fieldtype: "Select",
					options: "0\n1\n2\n3", default: record.mobility || "0",
				},
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
