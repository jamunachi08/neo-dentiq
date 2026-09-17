# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Practitioner", "fieldname": "practitioner", "fieldtype": "Link",
		 "options": "Dental Practitioner", "width": 180},
		{"label": "Procedures", "fieldname": "procedures", "fieldtype": "Int", "width": 100},
		{"label": "Production", "fieldname": "production", "fieldtype": "Currency",
		 "width": 130},
		{"label": "Chair Hours", "fieldname": "chair_hours", "fieldtype": "Float",
		 "width": 110},
		{"label": "Production / Hour", "fieldname": "per_hour", "fieldtype": "Currency",
		 "width": 150},
		{"label": "Lab Cost", "fieldname": "lab_cost", "fieldtype": "Currency",
		 "width": 110},
		{"label": "Commission %", "fieldname": "commission_rate", "fieldtype": "Percent",
		 "width": 120},
		{"label": "Commission Due", "fieldname": "commission", "fieldtype": "Currency",
		 "width": 140},
	]
	rows = frappe.db.sql("""
		select cp.practitioner, count(*) as procedures, sum(cp.rate) as production,
		       sum(coalesce(cp.chair_time_minutes, 0)) as chair_minutes
		from `tabClinical Procedure` cp
		where cp.docstatus = 1 and cp.procedure_date between %(from_date)s and %(to_date)s
		group by cp.practitioner
	""", filters, as_dict=True)
	for r in rows:
		r["chair_hours"] = round(flt(r.chair_minutes) / 60.0, 1)
		r["per_hour"] = round(flt(r.production) / r["chair_hours"], 2) \
			if r["chair_hours"] else 0
		r["lab_cost"] = flt(frappe.db.sql("""
			select sum(lab_cost) from `tabLab Case`
			where practitioner = %s and creation between %s and %s
		""", (r.practitioner, filters.from_date, filters.to_date))[0][0])
		meta = frappe.db.get_value("Dental Practitioner", r.practitioner,
		                           ["commission_rate", "lab_bill_to_practitioner"],
		                           as_dict=True) or {}
		rate = flt(meta.get("commission_rate"))
		base = flt(r.production) - (flt(r["lab_cost"])
		                            if meta.get("lab_bill_to_practitioner") else 0)
		r["commission_rate"] = rate
		r["commission"] = round(base * rate / 100.0, 2)
	return columns, rows
