"""Odontogram and perio-chart data services for the desk widgets."""
import json

import frappe
from frappe import _


@frappe.whitelist()
def get_odontogram(patient, numbering=None):
	chart_name = frappe.db.get_value("Dental Chart", {"patient": patient})
	if not chart_name:
		chart = frappe.new_doc("Dental Chart")
		chart.patient = patient
		chart.build_default_teeth()
		chart.insert(ignore_permissions=True)
		chart_name = chart.name
	chart = frappe.get_doc("Dental Chart", chart_name)
	numbering = numbering or chart.numbering_system

	teeth = frappe.get_all(
		"Tooth Master",
		filters={"dentition": chart.dentition} if chart.dentition != "Mixed" else {},
		fields=["name", "tooth_code", "universal_number", "palmer_notation",
		        "tooth_name", "arch", "quadrant", "tooth_type", "side", "dentition",
		        "surfaces"],
		order_by="quadrant asc, tooth_code asc",
	)
	entries = {r.tooth: r for r in chart.teeth}
	for tooth in teeth:
		entry = entries.get(tooth.name)
		tooth["label"] = {
			"FDI": tooth.tooth_code, "Universal": tooth.universal_number,
			"Palmer": tooth.palmer_notation,
		}.get(numbering, tooth.tooth_code)
		tooth["status"] = entry.status if entry else "Present"
		tooth["condition"] = entry.condition if entry else "Sound"
		tooth["treated_surfaces"] = entry.surfaces if entry else ""
		tooth["note"] = entry.note if entry else ""
		tooth["mobility"] = entry.mobility_grade if entry else "0"

	history = frappe.get_all(
		"Clinical Procedure",
		filters={"patient": patient, "docstatus": 1, "tooth": ["is", "set"]},
		fields=["name", "tooth", "procedure", "surfaces", "procedure_date",
		        "practitioner"],
		order_by="procedure_date desc", limit=200)

	planned = frappe.db.sql("""
		select tpi.tooth, tpi.procedure, tpi.surfaces, tpi.status, tpi.phase,
		       tp.name as treatment_plan
		from `tabTreatment Plan Item` tpi
		join `tabTreatment Plan` tp on tp.name = tpi.parent
		where tp.patient = %s and tp.docstatus = 1
		  and tpi.status in ('Proposed','Accepted','Scheduled','In Progress')
	""", patient, as_dict=True)

	return {
		"chart": chart_name,
		"numbering": numbering,
		"dentition": chart.dentition,
		"teeth": teeth,
		"history": history,
		"planned": planned,
		"indices": {"dmft": chart.dmft_score, "decayed": chart.decayed_count,
		            "missing": chart.missing_count, "filled": chart.filled_count},
	}


@frappe.whitelist()
def update_tooth(patient, tooth, status=None, condition=None, surfaces=None, note=None,
                 mobility_grade=None):
	chart_name = frappe.db.get_value("Dental Chart", {"patient": patient})
	chart = frappe.get_doc("Dental Chart", chart_name)
	payload = {k: v for k, v in {
		"status": status, "condition": condition, "surfaces": surfaces,
		"note": note, "mobility_grade": mobility_grade,
	}.items() if v is not None}
	chart.set_tooth(tooth, **payload)
	return {"ok": True, "indices": {"dmft": chart.dmft_score}}


@frappe.whitelist()
def get_perio_chart(patient, chart=None):
	if chart:
		doc = frappe.get_doc("Periodontal Chart", chart)
	else:
		name = frappe.db.get_value(
			"Periodontal Chart", {"patient": patient, "docstatus": ["<", 2]},
			"name", order_by="exam_date desc")
		if not name:
			return {"readings": [], "chart": None}
		doc = frappe.get_doc("Periodontal Chart", name)
	return {
		"chart": doc.name, "exam_date": str(doc.exam_date),
		"stage": doc.perio_stage, "grade": doc.perio_grade, "extent": doc.extent,
		"bop_percent": doc.bop_percent, "mean_pd": doc.mean_pd,
		"sites_5mm_plus": doc.sites_5mm_plus,
		"readings": [r.as_dict() for r in doc.readings],
	}


@frappe.whitelist()
def save_perio_readings(chart, readings):
	if isinstance(readings, str):
		readings = json.loads(readings)
	doc = frappe.get_doc("Periodontal Chart", chart)
	index = {r.tooth: r for r in doc.readings}
	for row in readings:
		target = index.get(row.get("tooth"))
		if not target:
			target = doc.append("readings", {"tooth": row.get("tooth")})
		for key, value in row.items():
			if key != "tooth" and hasattr(target, key):
				setattr(target, key, value)
	doc.save()
	return {"stage": doc.perio_stage, "grade": doc.perio_grade,
	        "bop_percent": doc.bop_percent, "mean_pd": doc.mean_pd}


@frappe.whitelist()
def compare_charts(patient, limit=4):
	"""Longitudinal perio comparison — shows whether therapy is working."""
	charts = frappe.get_all(
		"Periodontal Chart", filters={"patient": patient, "docstatus": 1},
		fields=["name", "exam_date", "bop_percent", "mean_pd", "sites_5mm_plus",
		        "perio_stage", "perio_grade", "plaque_index_percent"],
		order_by="exam_date desc", limit=int(limit))
	return list(reversed(charts))
