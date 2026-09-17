# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Item", "fieldname": "item_code", "fieldtype": "Link",
		 "options": "Item", "width": 220},
		{"label": "Batch / Lot", "fieldname": "batch_no", "fieldtype": "Link",
		 "options": "Batch", "width": 130},
		{"label": "Serial / UDI", "fieldname": "serial_no", "fieldtype": "Data",
		 "width": 150},
		{"label": "Expiry", "fieldname": "expiry_date", "fieldtype": "Date", "width": 100},
		{"label": "Patient", "fieldname": "patient", "fieldtype": "Link",
		 "options": "Patient", "width": 110},
		{"label": "Patient Name", "fieldname": "patient_name", "fieldtype": "Data",
		 "width": 160},
		{"label": "Date", "fieldname": "procedure_date", "fieldtype": "Datetime",
		 "width": 150},
		{"label": "Procedure", "fieldname": "procedure_doc", "fieldtype": "Link",
		 "options": "Clinical Procedure", "width": 140},
	]
	conditions = "cp.docstatus = 1"
	if filters.get("batch_no"):
		conditions += " and pcu.batch_no = %(batch_no)s"
	if filters.get("item_code"):
		conditions += " and pcu.item_code = %(item_code)s"
	rows = frappe.db.sql(f"""
		select pcu.item_code, pcu.batch_no, pcu.serial_no, pcu.expiry_date,
		       cp.patient, cp.patient_name, cp.procedure_date, cp.name as procedure_doc
		from `tabProcedure Consumable Used` pcu
		join `tabClinical Procedure` cp on cp.name = pcu.parent
		where {conditions} and (pcu.batch_no is not null or pcu.serial_no is not null)
		order by cp.procedure_date desc
	""", filters, as_dict=True)
	return columns, rows, (
		"Use this to answer a manufacturer recall: filter by lot and every affected "
		"patient appears with the exact procedure and date.")
