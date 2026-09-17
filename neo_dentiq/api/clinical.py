"""Chairside helpers used across the clinical workspace."""
import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate


@frappe.whitelist()
def patient_summary(patient):
	"""One call that powers the patient header on every clinical screen."""
	doc = frappe.get_doc("Patient", patient)
	doc.set_alert_summary()
	from neo_dentiq.utils.drug_safety import prophylaxis_required

	return {
		"patient": doc.name,
		"patient_name": doc.patient_name,
		"age": doc.age,
		"sex": doc.sex,
		"image": doc.image,
		"alerts": doc.flags.alert_list,
		"prophylaxis": prophylaxis_required(patient),
		"caries_risk": doc.caries_risk,
		"perio_risk": doc.perio_risk,
		"no_show_score": doc.no_show_score,
		"lifetime_value": doc.lifetime_value,
		"balance": _balance(doc.customer),
		"next_recall": str(doc.next_recall_date or ""),
		"last_visit": str(doc.last_visit_date or ""),
		"insurance": frappe.get_all(
			"Patient Insurance Policy",
			filters={"parent": patient, "parenttype": "Patient"},
			fields=["insurance_plan", "payer", "policy_number", "coverage_order",
			        "eligibility_status", "valid_to"]),
		"open_treatment_plans": frappe.get_all(
			"Treatment Plan",
			filters={"patient": patient, "docstatus": 1,
			         "status": ["in", ("Presented", "Partially Accepted", "Accepted",
			                           "In Progress")]},
			fields=["name", "title", "status", "total_patient_portion",
			        "acceptance_percent"]),
		"upcoming": frappe.get_all(
			"Dental Appointment",
			filters={"patient": patient, "appointment_date": [">=", nowdate()],
			         "status": ["not in", ("Cancelled", "No Show")]},
			fields=["name", "appointment_date", "appointment_time", "practitioner",
			        "appointment_type", "status"], order_by="appointment_date asc"),
		"cumulative_radiation_msv": doc.cumulative_radiation_msv,
	}


def _balance(customer):
	if not customer:
		return 0
	return flt(frappe.db.sql("""
		select sum(outstanding_amount) from `tabSales Invoice`
		where customer = %s and docstatus = 1
	""", customer)[0][0])


@frappe.whitelist()
def suggest_pathway(procedure, patient=None):
	"""Return the protocol steps for a procedure so a plan can be built in one click."""
	pathway = frappe.db.get_value("Dental Procedure", procedure, "clinical_pathway")
	if not pathway:
		return []
	return frappe.get_all(
		"Clinical Pathway Step", filters={"parent": pathway},
		fields=["step", "procedure", "step_description", "gap_days", "is_optional"],
		order_by="step asc")


@frappe.whitelist()
def build_plan_from_pathway(patient, practitioner, procedure, tooth=None):
	steps = suggest_pathway(procedure)
	if not steps:
		frappe.throw(_("No clinical pathway is linked to {0}.").format(procedure))
	plan = frappe.get_doc({
		"doctype": "Treatment Plan", "patient": patient, "practitioner": practitioner,
		"title": f"{procedure} pathway",
		"plan_date": nowdate(),
	})
	for step in steps:
		if not step.procedure:
			continue
		category = frappe.db.get_value("Dental Procedure", step.procedure, "category")
		phase = frappe.db.get_value("Dental Procedure Category", category,
		                            "default_phase")
		plan.append("items", {
			"phase": phase or "Phase 2 - Definitive / Restorative",
			"sequence": step.step, "procedure": step.procedure, "tooth": tooth,
			"notes": step.step_description,
			"is_recommended": 0 if step.is_optional else 1,
		})
	plan.insert()
	return plan.name


@frappe.whitelist()
def available_trays(instrument_kit, clinic=None):
	filters = {"instrument_kit": instrument_kit, "status": "Available (Sterile)",
	           "is_expired": 0, "last_cycle_result": "Pass"}
	if clinic:
		filters["clinic"] = clinic
	return frappe.get_all("Instrument Tray", filters=filters,
	                      fields=["name", "tray_code", "sterile_until", "last_cycle",
	                              "cycle_count"])


@frappe.whitelist()
def scan_tray(tray_code):
	"""Barcode scan endpoint for the chairside tray check."""
	tray = frappe.db.get_value(
		"Instrument Tray", tray_code,
		["name", "instrument_kit", "status", "sterile_until", "last_cycle",
		 "last_cycle_result", "is_expired", "cycle_count", "max_reuse_count"],
		as_dict=True)
	if not tray:
		frappe.throw(_("No instrument tray with code {0}.").format(tray_code))
	usable = (tray.status == "Available (Sterile)" and not tray.is_expired
	          and tray.last_cycle_result == "Pass")
	tray["usable"] = usable
	if not usable:
		tray["reason"] = (
			"Sterility expired" if tray.is_expired else
			"No passed cycle" if tray.last_cycle_result != "Pass" else
			f"Tray status is {tray.status}")
	return tray


@frappe.whitelist()
def cumulative_dose(patient):
	"""Radiation dose audit (ALARA / IR(ME)R)."""
	rows = frappe.get_all(
		"Radiograph Record", filters={"patient": patient},
		fields=["name", "radiograph_type", "exposure_datetime", "effective_dose_msv",
		        "is_repeat"], order_by="exposure_datetime desc")
	total = sum(flt(r.effective_dose_msv) for r in rows)
	last_year = sum(flt(r.effective_dose_msv) for r in rows
	                if getdate(r.exposure_datetime) >= getdate(add_days(nowdate(), -365)))
	return {"total_msv": round(total, 4), "last_12_months_msv": round(last_year, 4),
	        "exposures": rows, "repeat_rate": round(
			len([r for r in rows if r.is_repeat]) * 100.0 / len(rows), 1) if rows else 0}
