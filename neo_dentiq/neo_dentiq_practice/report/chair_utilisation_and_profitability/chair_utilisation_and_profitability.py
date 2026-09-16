# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import date_diff, flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Operatory", "fieldname": "operatory", "fieldtype": "Link",
		 "options": "Dental Operatory", "width": 160},
		{"label": "Clinic", "fieldname": "clinic", "fieldtype": "Link",
		 "options": "Dental Clinic", "width": 140},
		{"label": "Appointments", "fieldname": "appointments", "fieldtype": "Int",
		 "width": 110},
		{"label": "Booked Hours", "fieldname": "booked_hours", "fieldtype": "Float",
		 "width": 110},
		{"label": "Delivered Hours", "fieldname": "used_hours", "fieldtype": "Float",
		 "width": 120},
		{"label": "Utilisation %", "fieldname": "utilisation", "fieldtype": "Percent",
		 "width": 110},
		{"label": "Production", "fieldname": "production", "fieldtype": "Currency",
		 "width": 130},
		{"label": "Production / Chair Hour", "fieldname": "per_hour",
		 "fieldtype": "Currency", "width": 170},
		{"label": "Operating Cost", "fieldname": "operating_cost",
		 "fieldtype": "Currency", "width": 130},
		{"label": "Contribution", "fieldname": "contribution", "fieldtype": "Currency",
		 "width": 130},
	]

	conditions = "a.appointment_date between %(from_date)s and %(to_date)s"
	if filters.get("clinic"):
		conditions += " and a.clinic = %(clinic)s"

	rows = frappe.db.sql(f"""
		select a.operatory, a.clinic, count(*) as appointments,
		       sum(a.duration) as booked_minutes,
		       sum(case when a.status = 'Completed' then a.duration else 0 end)
		         as used_minutes,
		       sum(coalesce(a.production_value, 0)) as production
		from `tabDental Appointment` a
		where {conditions} and a.status not in ('Cancelled', 'Rescheduled')
		group by a.operatory, a.clinic
	""", filters, as_dict=True)

	days = max(date_diff(filters.get("to_date"), filters.get("from_date")), 1)
	working_days = days * 5 / 7.0
	capacity_minutes = working_days * 8 * 60

	for r in rows:
		r["booked_hours"] = round(flt(r.booked_minutes) / 60.0, 1)
		r["used_hours"] = round(flt(r.used_minutes) / 60.0, 1)
		r["utilisation"] = round(flt(r.used_minutes) * 100.0 / capacity_minutes, 1) \
			if capacity_minutes else 0
		r["per_hour"] = round(flt(r.production) / (flt(r.used_minutes) / 60.0), 2) \
			if r.used_minutes else 0
		cost_rate = flt(frappe.db.get_value("Dental Operatory", r.operatory,
		                                    "hourly_operating_cost"))
		r["operating_cost"] = round(cost_rate * flt(r.used_minutes) / 60.0, 2)
		r["contribution"] = round(flt(r.production) - r["operating_cost"], 2)

	chart = {
		"data": {"labels": [r.operatory for r in rows],
		         "datasets": [{"name": "Utilisation %",
		                       "values": [r["utilisation"] for r in rows]}]},
		"type": "bar",
	}
	return columns, rows, None, chart
