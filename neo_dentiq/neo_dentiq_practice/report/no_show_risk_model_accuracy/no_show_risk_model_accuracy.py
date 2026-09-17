# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Risk Band", "fieldname": "risk_band", "fieldtype": "Data", "width": 120},
		{"label": "Appointments", "fieldname": "total", "fieldtype": "Int", "width": 120},
		{"label": "No Shows", "fieldname": "no_shows", "fieldtype": "Int", "width": 110},
		{"label": "Actual No-Show %", "fieldname": "actual_rate", "fieldtype": "Percent",
		 "width": 150},
		{"label": "Avg Predicted %", "fieldname": "predicted", "fieldtype": "Percent",
		 "width": 150},
		{"label": "Calibration Gap", "fieldname": "gap", "fieldtype": "Float", "width": 130},
	]
	rows = frappe.db.sql("""
		select coalesce(risk_band, 'Unscored') as risk_band, count(*) as total,
		       sum(case when status = 'No Show' then 1 else 0 end) as no_shows,
		       round(sum(case when status = 'No Show' then 1 else 0 end) * 100.0
		             / count(*), 1) as actual_rate,
		       round(avg(no_show_risk), 1) as predicted
		from `tabDental Appointment`
		where appointment_date between %(from_date)s and %(to_date)s
		  and status in ('Completed','No Show')
		group by risk_band
	""", filters, as_dict=True)
	for r in rows:
		r["gap"] = round((r.predicted or 0) - (r.actual_rate or 0), 1)
	return columns, rows, (
		"A well-calibrated model shows the High band with a materially higher actual "
		"no-show rate than the Low band. The calibration gap should trend to zero.")
