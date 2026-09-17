# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Practitioner", "fieldname": "practitioner", "fieldtype": "Link",
		 "options": "Dental Practitioner", "width": 180},
		{"label": "Plans Presented", "fieldname": "plans", "fieldtype": "Int", "width": 130},
		{"label": "Value Presented", "fieldname": "presented", "fieldtype": "Currency",
		 "width": 150},
		{"label": "Value Accepted", "fieldname": "accepted", "fieldtype": "Currency",
		 "width": 150},
		{"label": "Acceptance %", "fieldname": "rate", "fieldtype": "Percent",
		 "width": 120},
		{"label": "Declined Value", "fieldname": "declined", "fieldtype": "Currency",
		 "width": 140},
		{"label": "Avg Plan Value", "fieldname": "avg_plan", "fieldtype": "Currency",
		 "width": 140},
	]
	conditions = "tp.docstatus = 1 and tp.plan_date between %(from_date)s and %(to_date)s"
	if filters.get("clinic"):
		conditions += " and tp.clinic = %(clinic)s"
	rows = frappe.db.sql(f"""
		select tp.practitioner, count(*) as plans, sum(tp.total_fee) as presented,
		       sum(tp.accepted_fee) as accepted
		from `tabTreatment Plan` tp where {conditions}
		group by tp.practitioner
	""", filters, as_dict=True)
	for r in rows:
		r["rate"] = round(flt(r.accepted) * 100.0 / flt(r.presented), 1) \
			if r.presented else 0
		r["declined"] = flt(r.presented) - flt(r.accepted)
		r["avg_plan"] = round(flt(r.presented) / r.plans, 2) if r.plans else 0
	chart = {
		"data": {"labels": [r.practitioner for r in rows],
		         "datasets": [{"name": "Acceptance %", "values": [r["rate"] for r in rows]}]},
		"type": "bar",
	}
	return columns, rows, "Case acceptance is the single biggest lever on practice " \
	                      "revenue. Below 50% usually signals a presentation problem, " \
	                      "not a pricing problem.", chart
