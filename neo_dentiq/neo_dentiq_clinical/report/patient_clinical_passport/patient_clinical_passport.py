# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("patient"):
		return [], []
	columns = [
		{"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 110},
		{"label": "Event", "fieldname": "event", "fieldtype": "Data", "width": 150},
		{"label": "Detail", "fieldname": "detail", "fieldtype": "Data", "width": 320},
		{"label": "Tooth", "fieldname": "tooth", "fieldtype": "Data", "width": 80},
		{"label": "Practitioner", "fieldname": "practitioner", "fieldtype": "Data",
		 "width": 160},
		{"label": "Reference", "fieldname": "reference", "fieldtype": "Dynamic Link",
		 "options": "doctype", "width": 150},
		{"label": "doctype", "fieldname": "doctype", "fieldtype": "Data", "hidden": 1},
	]
	rows = []
	patient = filters.patient

	for r in frappe.get_all("Clinical Procedure",
	                        filters={"patient": patient, "docstatus": 1},
	                        fields=["name", "procedure_date", "procedure", "tooth",
	                                "practitioner", "surfaces", "outcome"]):
		rows.append({"date": r.procedure_date, "event": "Procedure",
		             "detail": f"{r.procedure} ({r.outcome})", "tooth": r.tooth,
		             "practitioner": r.practitioner, "reference": r.name,
		             "doctype": "Clinical Procedure"})
	for r in frappe.get_all("Dental Prescription",
	                        filters={"patient": patient, "docstatus": 1},
	                        fields=["name", "prescription_date", "diagnosis",
	                                "practitioner"]):
		rows.append({"date": r.prescription_date, "event": "Prescription",
		             "detail": r.diagnosis or "Medication issued",
		             "practitioner": r.practitioner, "reference": r.name,
		             "doctype": "Dental Prescription"})
	for r in frappe.get_all("Radiograph Record", filters={"patient": patient},
	                        fields=["name", "exposure_datetime", "radiograph_type",
	                                "practitioner", "effective_dose_msv"]):
		rows.append({"date": r.exposure_datetime, "event": "Radiograph",
		             "detail": f"{r.radiograph_type} ({r.effective_dose_msv} mSv)",
		             "practitioner": r.practitioner, "reference": r.name,
		             "doctype": "Radiograph Record"})
	for r in frappe.get_all("Implant Record", filters={"patient": patient},
	                        fields=["name", "placement_date", "brand", "tooth",
	                                "practitioner", "serial_no", "status"]):
		rows.append({"date": r.placement_date, "event": "Implant",
		             "detail": f"{r.brand or 'Implant'} · UDI {r.serial_no or 'n/a'} · {r.status}",
		             "tooth": r.tooth, "practitioner": r.practitioner,
		             "reference": r.name, "doctype": "Implant Record"})
	for r in frappe.get_all("Periodontal Chart",
	                        filters={"patient": patient, "docstatus": 1},
	                        fields=["name", "exam_date", "perio_stage", "perio_grade",
	                                "bop_percent", "practitioner"]):
		rows.append({"date": r.exam_date, "event": "Perio Chart",
		             "detail": f"{r.perio_stage} {r.perio_grade}, BOP {r.bop_percent}%",
		             "practitioner": r.practitioner, "reference": r.name,
		             "doctype": "Periodontal Chart"})
	for r in frappe.get_all("Consent Record", filters={"patient": patient},
	                        fields=["name", "consent_date", "consent_template",
	                                "status", "practitioner"]):
		rows.append({"date": r.consent_date, "event": "Consent",
		             "detail": f"{r.consent_template} ({r.status})",
		             "practitioner": r.practitioner, "reference": r.name,
		             "doctype": "Consent Record"})

	rows.sort(key=lambda x: str(x["date"]), reverse=True)
	return columns, rows
