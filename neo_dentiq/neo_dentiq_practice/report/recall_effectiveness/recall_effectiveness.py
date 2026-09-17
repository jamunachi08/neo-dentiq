# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Recall Type", "fieldname": "recall_type", "fieldtype": "Link",
		 "options": "Recall Type", "width": 200},
		{"label": "Due", "fieldname": "due", "fieldtype": "Int", "width": 90},
		{"label": "Contacted", "fieldname": "contacted", "fieldtype": "Int", "width": 100},
		{"label": "Booked", "fieldname": "booked", "fieldtype": "Int", "width": 90},
		{"label": "Completed", "fieldname": "completed", "fieldtype": "Int", "width": 100},
		{"label": "Overdue", "fieldname": "overdue", "fieldtype": "Int", "width": 90},
		{"label": "Conversion %", "fieldname": "rate", "fieldtype": "Percent", "width": 120},
	]
	rows = frappe.db.sql("""
		select recall_type, count(*) as due,
		       sum(case when status = 'Contacted' then 1 else 0 end) as contacted,
		       sum(case when status = 'Booked' then 1 else 0 end) as booked,
		       sum(case when status = 'Completed' then 1 else 0 end) as completed,
		       sum(case when status = 'Overdue' then 1 else 0 end) as overdue,
		       round((sum(case when status in ('Booked','Completed') then 1 else 0 end))
		             * 100.0 / count(*), 1) as rate
		from `tabRecall Schedule`
		where due_date between %(from_date)s and %(to_date)s
		group by recall_type
	""", filters, as_dict=True)
	return columns, rows
