# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Claim", "fieldname": "name", "fieldtype": "Link",
		 "options": "Insurance Claim", "width": 140},
		{"label": "Payer", "fieldname": "payer", "fieldtype": "Link",
		 "options": "Insurance Payer", "width": 160},
		{"label": "Patient", "fieldname": "patient_name", "fieldtype": "Data", "width": 160},
		{"label": "Claim Date", "fieldname": "claim_date", "fieldtype": "Date", "width": 100},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
		{"label": "Aging (days)", "fieldname": "aging_days", "fieldtype": "Int", "width": 100},
		{"label": "Bucket", "fieldname": "bucket", "fieldtype": "Data", "width": 90},
		{"label": "Billed", "fieldname": "total_billed", "fieldtype": "Currency",
		 "width": 110},
		{"label": "Paid", "fieldname": "total_paid", "fieldtype": "Currency", "width": 110},
		{"label": "Outstanding", "fieldname": "outstanding", "fieldtype": "Currency",
		 "width": 120},
		{"label": "Filing Deadline", "fieldname": "filing_deadline", "fieldtype": "Date",
		 "width": 120},
		{"label": "Risk", "fieldname": "risk", "fieldtype": "Data", "width": 110},
	]
	rows = frappe.db.sql("""
		select name, payer, patient_name, claim_date, status, aging_days,
		       total_billed, total_paid, outstanding, filing_deadline
		from `tabInsurance Claim`
		where docstatus = 1 and outstanding > 0
		  and claim_date between %(from_date)s and %(to_date)s
		order by aging_days desc
	""", filters, as_dict=True)
	from frappe.utils import date_diff, nowdate
	for r in rows:
		age = r.aging_days or 0
		r["bucket"] = ("0-30" if age <= 30 else "31-60" if age <= 60
		               else "61-90" if age <= 90 else "90+")
		left = date_diff(r.filing_deadline, nowdate()) if r.filing_deadline else 999
		r["risk"] = ("Deadline passed" if left < 0 else
		             "Deadline < 14d" if left <= 14 else "")
	total = sum(flt(r.outstanding) for r in rows)
	at_risk = sum(flt(r.outstanding) for r in rows if r["risk"])
	return columns, rows, (
		f"Outstanding with payers: {total:,.2f}. At filing-deadline risk: {at_risk:,.2f}.")
