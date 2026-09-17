frappe.query_reports["Material and Implant Traceability"] = {
	filters: [
		{fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item"},
		{fieldname: "batch_no", label: __("Batch / Lot"), fieldtype: "Link", options: "Batch"},
	],
};
