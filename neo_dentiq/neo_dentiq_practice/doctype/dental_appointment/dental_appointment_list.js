frappe.listview_settings["Dental Appointment"] = {
	add_fields: ["status", "no_show_risk", "risk_band", "appointment_date"],

	get_indicator(doc) {
		const entry = neo_dentiq.theme.entry("appointment_status", doc.status);
		if (entry && neo_dentiq.theme.enabled("coloured_status_pills")) {
			// Colour comes from Neo Dentiq Theme so a practice can recolour the diary.
			return [__(entry.label || doc.status), entry.colour, `status,=,${doc.status}`];
		}
		const fallback = {
			Requested: "purple", Scheduled: "blue", Confirmed: "light-blue",
			Arrived: "cyan", "In Operatory": "purple", "In Progress": "blue",
			Completed: "green", Cancelled: "gray", "No Show": "red",
			Rescheduled: "orange",
		};
		return [__(doc.status), fallback[doc.status] || "gray", `status,=,${doc.status}`];
	},

	formatters: {
		no_show_risk(value, df, doc) {
			if (!value) return "";
			const tone = doc.risk_band === "High" ? "danger"
				: doc.risk_band === "Medium" ? "warning" : "success";
			return `<span class="ndq-pill" data-tone="${tone}">${value}%</span>`;
		},
	},
};
