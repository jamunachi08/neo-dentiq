"""Behavioural no-show risk model.

Transparent, explainable, weighted-feature scoring. It needs no external
service and trains itself on the practice's own history by recalibrating
feature weights against realised outcomes.
"""
import frappe
from frappe.utils import (add_days, cint, date_diff, flt, get_datetime, getdate,
                          nowdate, now_datetime)

WEIGHTS = {
	"prior_no_shows": 14,
	"prior_late_cancels": 7,
	"new_patient": 8,
	"long_lead_time": 6,
	"monday_or_friday": 3,
	"early_morning": 5,
	"late_afternoon": 4,
	"no_confirmation": 12,
	"no_contact_channel": 6,
	"outstanding_balance": 9,
	"long_gap_since_visit": 8,
	"high_cost_treatment": 5,
	"no_insurance": 4,
	"rescheduled_before": 6,
}

LABELS = {
	"prior_no_shows": "History of no-shows",
	"prior_late_cancels": "History of late cancellations",
	"new_patient": "First visit",
	"long_lead_time": "Booked far in advance",
	"monday_or_friday": "Monday/Friday slot",
	"early_morning": "Early morning slot",
	"late_afternoon": "Late afternoon slot",
	"no_confirmation": "Not yet confirmed",
	"no_contact_channel": "No reachable contact channel",
	"outstanding_balance": "Outstanding balance",
	"long_gap_since_visit": "Long gap since last visit",
	"high_cost_treatment": "High-value treatment",
	"no_insurance": "Self-pay, no insurance",
	"rescheduled_before": "Previously rescheduled",
}


def score_appointment(appointment):
	features = extract_features(appointment)
	weights = load_weights()
	score = sum(weights.get(k, 0) for k, v in features.items() if v)
	score = max(0, min(int(score), 99))
	factors = [LABELS[k] for k, v in features.items() if v and weights.get(k, 0) >= 5]
	return {"score": score, "band": band(score), "factors": factors,
	        "features": features}


def band(score):
	if score >= 60:
		return "High"
	if score >= 30:
		return "Medium"
	return "Low"


def extract_features(appointment):
	patient = appointment.patient
	hist = frappe.db.sql("""
		select status, count(*) as c from `tabDental Appointment`
		where patient = %s and name != %s group by status
	""", (patient, appointment.name or ""), as_dict=True)
	counts = {r.status: r.c for r in hist}

	pdoc = frappe.db.get_value(
		"Patient", patient,
		["mobile", "email", "last_visit_date", "customer", "preferred_contact_method"],
		as_dict=True) or {}

	apt_dt = get_datetime(f"{appointment.appointment_date} {appointment.appointment_time}")
	lead_days = date_diff(appointment.appointment_date, nowdate())
	hour = apt_dt.hour
	weekday = getdate(appointment.appointment_date).weekday()

	balance = 0
	if pdoc.get("customer"):
		balance = flt(frappe.db.sql("""
			select sum(outstanding_amount) from `tabSales Invoice`
			where customer = %s and docstatus = 1 and outstanding_amount > 0
		""", pdoc["customer"])[0][0])

	fee = sum(flt(r.fee) for r in appointment.get("procedures") or [])
	has_insurance = bool(frappe.db.exists(
		"Patient Insurance Policy", {"parent": patient, "parenttype": "Patient"}))

	gap = date_diff(nowdate(), pdoc["last_visit_date"]) if pdoc.get("last_visit_date") else 999

	return {
		"prior_no_shows": counts.get("No Show", 0) >= 1,
		"prior_late_cancels": counts.get("Cancelled", 0) >= 2,
		"new_patient": bool(appointment.is_new_patient),
		"long_lead_time": lead_days > 21,
		"monday_or_friday": weekday in (0, 4),
		"early_morning": hour < 9,
		"late_afternoon": hour >= 17,
		"no_confirmation": appointment.confirmation_status != "Confirmed by Patient",
		"no_contact_channel": not (pdoc.get("mobile") or pdoc.get("email")),
		"outstanding_balance": balance > 0,
		"long_gap_since_visit": gap > 365,
		"high_cost_treatment": fee > 1000,
		"no_insurance": not has_insurance,
		"rescheduled_before": counts.get("Rescheduled", 0) >= 1,
	}


def load_weights():
	cached = frappe.cache().get_value("neo_dentiq_no_show_weights")
	return cached or WEIGHTS


def record_no_show(appointment):
	"""Update the patient's rolling behavioural score and charge any no-show fee."""
	patient = appointment.patient
	stats = frappe.db.sql("""
		select
			sum(case when status = 'No Show' then 1 else 0 end) as no_shows,
			count(*) as total
		from `tabDental Appointment` where patient = %s
	""", patient, as_dict=True)[0]
	total = stats.total or 1
	rate = int((stats.no_shows or 0) * 100.0 / total)
	frappe.db.set_value("Patient", patient, "no_show_score", rate)

	if not appointment.cancellation_reason:
		return
	chargeable = frappe.db.get_value(
		"Cancellation Reason", appointment.cancellation_reason, "chargeable")
	fee_item = frappe.db.get_single_value("Neo Dentiq Settings", "no_show_fee_item")
	if chargeable and fee_item:
		from neo_dentiq.utils.billing import charge_no_show_fee
		charge_no_show_fee(appointment, fee_item)


def recalibrate_weights():
	"""Nightly: reweight features by their realised lift against the base rate.

	For each feature, compare the no-show rate of appointments that had it against
	the overall rate. Features that do not discriminate decay toward zero, so the
	model adapts to each practice without any external training pipeline.
	"""
	rows = frappe.get_all(
		"Dental Appointment",
		filters={"status": ["in", ("Completed", "No Show")],
		         "appointment_date": [">=", add_days(nowdate(), -365)]},
		fields=["name", "status", "risk_factors"],
		limit=5000,
	)
	if len(rows) < 100:
		return
	base_rate = len([r for r in rows if r.status == "No Show"]) * 1.0 / len(rows)
	if base_rate <= 0:
		return
	tuned = {}
	for key, label in LABELS.items():
		with_feature = [r for r in rows if r.risk_factors and label in r.risk_factors]
		if len(with_feature) < 20:
			tuned[key] = WEIGHTS[key]
			continue
		rate = len([r for r in with_feature if r.status == "No Show"]) * 1.0 / len(with_feature)
		lift = rate / base_rate
		tuned[key] = max(0, min(25, round(WEIGHTS[key] * lift)))
	frappe.cache().set_value("neo_dentiq_no_show_weights", tuned, expires_in_sec=7 * 86400)
	return tuned


def rescore_upcoming():
	"""Scheduled job: refresh risk for the next 30 days of appointments."""
	names = frappe.get_all(
		"Dental Appointment",
		filters={"appointment_date": ["between", (nowdate(), add_days(nowdate(), 30))],
		         "status": ["in", ("Requested", "Scheduled", "Confirmed")]},
		pluck="name",
	)
	for name in names:
		doc = frappe.get_doc("Dental Appointment", name)
		result = score_appointment(doc)
		frappe.db.set_value("Dental Appointment", name, {
			"no_show_risk": result["score"],
			"risk_band": result["band"],
			"risk_factors": "; ".join(result["factors"]),
		}, update_modified=False)
	frappe.db.commit()
