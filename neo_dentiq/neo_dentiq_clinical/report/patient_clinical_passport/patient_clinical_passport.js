frappe.query_reports["Patient Clinical Passport"] = {
	filters: [
		{fieldname: "patient", label: __("Patient"), fieldtype: "Link",
		 options: "Patient", reqd: 1},
	],
};
