"""Patient-facing portal services."""
import frappe
from frappe import _
from frappe.utils import nowdate


def _me():
	patient = frappe.db.get_value("Patient", {"user": frappe.session.user}, "name")
	if not patient:
		patient = frappe.db.get_value(
			"Patient", {"email": frappe.session.user}, "name")
	if not patient:
		frappe.throw(_("No patient record is linked to your login."),
		             frappe.PermissionError)
	return patient


@frappe.whitelist()
def my_dashboard():
	patient = _me()
	doc = frappe.get_doc("Patient", patient)
	return {
		"name": doc.patient_name,
		"next_recall": str(doc.next_recall_date or ""),
		"appointments": frappe.get_all(
			"Dental Appointment", filters={"patient": patient},
			fields=["name", "appointment_date", "appointment_time", "practitioner",
			        "appointment_type", "status"],
			order_by="appointment_date desc", limit=10),
		"treatment_plans": frappe.get_all(
			"Treatment Plan", filters={"patient": patient, "docstatus": 1},
			fields=["name", "title", "status", "total_fee", "total_patient_portion",
			        "total_insurance_estimate"]),
		"prescriptions": frappe.get_all(
			"Dental Prescription", filters={"patient": patient, "docstatus": 1},
			fields=["name", "prescription_date", "practitioner", "diagnosis"],
			order_by="prescription_date desc", limit=10),
		"invoices": frappe.get_all(
			"Sales Invoice", filters={"neo_dentiq_patient": patient, "docstatus": 1},
			fields=["name", "posting_date", "grand_total", "outstanding_amount",
			        "status"], order_by="posting_date desc", limit=10),
		"payment_plans": frappe.get_all(
			"Patient Payment Plan", filters={"patient": patient, "status": "Active"},
			fields=["name", "total_amount", "amount_paid", "outstanding",
			        "next_due_date"]),
	}


@frappe.whitelist()
def accept_treatment_plan(treatment_plan, signature=None, items=None):
	patient = _me()
	plan = frappe.get_doc("Treatment Plan", treatment_plan)
	if plan.patient != patient:
		frappe.throw(_("Not your treatment plan."), frappe.PermissionError)
	if items:
		import json
		chosen = json.loads(items) if isinstance(items, str) else items
		for row in plan.items:
			row.status = "Accepted" if row.name in chosen else "Declined"
	else:
		for row in plan.items:
			if row.status == "Proposed":
				row.status = "Accepted"
	if signature:
		plan.patient_signature = signature
		plan.signed_on = frappe.utils.now_datetime()
	plan.save(ignore_permissions=True)
	return plan.status


@frappe.whitelist()
def submit_intake(response, answers, signature=None):
	import json
	patient = _me()
	doc = frappe.get_doc("Patient Intake Response", response)
	if doc.patient and doc.patient != patient:
		frappe.throw(_("Not your form."), frappe.PermissionError)
	doc.patient = patient
	doc.answers = []
	for row in (json.loads(answers) if isinstance(answers, str) else answers):
		doc.append("answers", row)
	doc.status = "Submitted"
	doc.submitted_on = frappe.utils.now_datetime()
	if signature:
		doc.patient_signature = signature
		doc.signed_on = frappe.utils.now_datetime()
	doc.save(ignore_permissions=True)
	_apply_intake_to_patient(doc)
	if doc.appointment:
		frappe.db.set_value("Dental Appointment", doc.appointment, "intake_status",
		                    "Completed")
	return doc.name


def _apply_intake_to_patient(response):
	"""Push structured intake answers into the patient's clinical record."""
	patient = frappe.get_doc("Patient", response.patient)
	changed = False
	for row in response.answers:
		if not row.answer:
			continue
		if row.maps_to == "Allergy":
			for token in str(row.answer).split(","):
				token = token.strip()
				if token and frappe.db.exists("Allergy Master", token) and not any(
					a.allergy == token for a in patient.allergies):
					patient.append("allergies", {"allergy": token, "verified": 0})
					changed = True
		elif row.maps_to == "Medical Alert":
			for token in str(row.answer).split(","):
				token = token.strip()
				if token and frappe.db.exists("Medical Alert Master", token) and not any(
					m.medical_alert == token for m in patient.medical_alerts):
					patient.append("medical_alerts", {"medical_alert": token})
					changed = True
		elif row.maps_to == "Smoking Status" and row.answer in (
			"Never", "Former", "Current - Light", "Current - Heavy"):
			patient.smoking_status = row.answer
			changed = True
		elif row.maps_to == "Pregnancy" and str(row.answer) in ("1", "Yes", "true"):
			patient.is_pregnant = 1
			changed = True
	if changed:
		patient.history_last_reviewed = nowdate()
		patient.save(ignore_permissions=True)


@frappe.whitelist()
def cancel_my_appointment(appointment, reason=None):
	patient = _me()
	doc = frappe.get_doc("Dental Appointment", appointment)
	if doc.patient != patient:
		frappe.throw(_("Not your appointment."), frappe.PermissionError)
	doc.status = "Cancelled"
	doc.cancellation_reason = reason if reason and frappe.db.exists(
		"Cancellation Reason", reason) else None
	doc.save(ignore_permissions=True)
	return doc.status
