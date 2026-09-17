import "./theme.js";
import "./odontogram.js";
import "./perio_chart.js";
import "./patient_banner.js";

frappe.provide("neo_dentiq");

neo_dentiq.format_tooth = function (tooth) {
	return tooth ? `#${tooth}` : "";
};

frappe.realtime.on("neo_dentiq_alert", (data) => {
	frappe.show_alert({ message: `${data.title}: ${data.message}`, indicator: "orange" }, 10);
});
