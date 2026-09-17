# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Procedure", "fieldname": "procedure_doc", "fieldtype": "Link",
		 "options": "Clinical Procedure", "width": 150},
		{"label": "Date", "fieldname": "procedure_date", "fieldtype": "Datetime",
		 "width": 160},
		{"label": "Patient", "fieldname": "patient", "fieldtype": "Link",
		 "options": "Patient", "width": 120},
		{"label": "Patient Name", "fieldname": "patient_name", "fieldtype": "Data",
		 "width": 160},
		{"label": "Treatment", "fieldname": "procedure", "fieldtype": "Data", "width": 180},
		{"label": "Tray", "fieldname": "instrument_tray", "fieldtype": "Link",
		 "options": "Instrument Tray", "width": 120},
		{"label": "Cycle", "fieldname": "sterilization_cycle", "fieldtype": "Link",
		 "options": "Sterilization Cycle", "width": 140},
		{"label": "Cycle Result", "fieldname": "cycle_result", "fieldtype": "Data",
		 "width": 110},
		{"label": "Chain Intact", "fieldname": "chain", "fieldtype": "Data", "width": 110},
	]
	conditions = "cp.docstatus = 1 and cp.procedure_date between %(from_date)s and %(to_date)s"
	if filters.get("clinic"):
		conditions += " and cp.clinic = %(clinic)s"
	rows = frappe.db.sql(f"""
		select cp.name as procedure_doc, cp.procedure_date, cp.patient, cp.patient_name,
		       cp.procedure, ptu.instrument_tray, ptu.sterilization_cycle,
		       ptu.cycle_result
		from `tabClinical Procedure` cp
		left join `tabProcedure Tray Used` ptu on ptu.parent = cp.name
		where {conditions}
		order by cp.procedure_date desc
	""", filters, as_dict=True)
	for r in rows:
		if not r.instrument_tray:
			r["chain"] = "No tray logged"
		elif r.cycle_result == "Pass":
			r["chain"] = "Yes"
		else:
			r["chain"] = "BROKEN"
	broken = len([r for r in rows if r["chain"] != "Yes"])
	message = (f"{broken} of {len(rows)} procedure records have an incomplete "
	           "sterilisation chain." if broken else
	           "Every procedure in this period traces back to a passed sterilisation cycle.")
	return columns, rows, message
