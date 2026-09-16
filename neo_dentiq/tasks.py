"""Scheduled jobs."""
import frappe
from frappe.utils import add_days, add_months, cint, getdate, nowdate, now_datetime


def send_appointment_reminders():
	from neo_dentiq.utils.messaging import send_appointment_reminder
	settings = frappe.get_single("Neo Dentiq Settings")
	offsets = [int(x) for x in (settings.reminder_offsets_hours or "24").split(",")
	           if x.strip().isdigit()]
	for hours in offsets:
		target = add_days(nowdate(), hours // 24)
		names = frappe.get_all("Dental Appointment", filters={
			"appointment_date": target,
			"status": ["in", ("Scheduled", "Confirmed", "Requested")],
		}, pluck="name")
		for name in names:
			doc = frappe.get_doc("Dental Appointment", name)
			if cint(doc.reminder_count) >= len(offsets):
				continue
			try:
				send_appointment_reminder(doc)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Neo Dentiq reminder")
	frappe.db.commit()


def rescore_no_show_risk():
	from neo_dentiq.utils.no_show import rescore_upcoming
	rescore_upcoming()


def recalibrate_no_show_model():
	from neo_dentiq.utils.no_show import recalibrate_weights
	recalibrate_weights()


def refresh_patient_metrics():
	from neo_dentiq.utils.metrics import recompute_patient_metrics
	recompute_patient_metrics()


def generate_due_recalls():
	"""Create the next recall for patients whose cycle has come round."""
	patients = frappe.get_all("Patient", filters={
		"status": "Active", "next_recall_date": ["<=", nowdate()],
	}, fields=["name", "recall_type", "primary_practitioner", "clinic", "caries_risk"])
	default_type = frappe.db.get_single_value("Neo Dentiq Settings", "default_recall_type")
	for p in patients:
		rtype = p.recall_type or default_type
		if not rtype:
			continue
		if frappe.db.exists("Recall Schedule", {
			"patient": p.name, "status": ["in", ("Due", "Contacted", "Overdue")]}):
			continue
		rt = frappe.get_cached_doc("Recall Type", rtype)
		months = {"Low": rt.low_risk_months, "Moderate": rt.moderate_risk_months,
		          "High": rt.high_risk_months, "Extreme": rt.high_risk_months}.get(
			p.caries_risk) or rt.interval_months
		due = add_months(nowdate(), months)
		frappe.get_doc({
			"doctype": "Recall Schedule", "patient": p.name, "recall_type": rtype,
			"due_date": due, "interval_months": months, "risk_adjusted": 1,
			"practitioner": p.primary_practitioner, "clinic": p.clinic,
		}).insert(ignore_permissions=True)
		frappe.db.set_value("Patient", p.name, "next_recall_date", due,
		                    update_modified=False)
	frappe.db.commit()


def escalate_overdue_recalls():
	from neo_dentiq.utils.messaging import send_recall
	rows = frappe.get_all("Recall Schedule", filters={
		"status": ["in", ("Due", "Overdue")],
		"due_date": ["<=", add_days(nowdate(), 14)],
	}, fields=["name", "patient", "contact_attempts", "last_contacted_on"])
	for row in rows:
		if cint(row.contact_attempts) >= 3:
			continue
		if row.last_contacted_on and getdate(row.last_contacted_on) > getdate(
			add_days(nowdate(), -7)):
			continue
		try:
			send_recall(frappe.get_doc("Recall Schedule", row.name))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Neo Dentiq recall")
	frappe.db.sql("""update `tabRecall Schedule` set status = 'Overdue'
	                 where status = 'Due' and due_date < %s""", nowdate())
	frappe.db.commit()


def expire_consents():
	frappe.db.sql("""update `tabConsent Record` set status = 'Expired'
	                 where status = 'Signed' and valid_till < %s""", nowdate())
	frappe.db.commit()


def flag_expired_sterile_trays():
	rows = frappe.get_all("Instrument Tray", filters={
		"sterile_until": ["<", nowdate()], "status": "Available (Sterile)"}, pluck="name")
	for name in rows:
		frappe.db.set_value("Instrument Tray", name, {
			"is_expired": 1, "status": "Dirty / Awaiting Reprocessing",
		}, update_modified=False)
	frappe.db.commit()


def sterilizer_validation_alerts():
	rows = frappe.get_all("Sterilizer", filters={
		"next_validation_due": ["<=", add_days(nowdate(), 30)], "is_active": 1},
		fields=["name", "next_validation_due"])
	for row in rows:
		frappe.publish_realtime("neo_dentiq_alert", {
			"title": "Sterilizer validation due",
			"message": f"{row.name} is due for validation on {row.next_validation_due}.",
		})


def age_insurance_claims():
	claims = frappe.get_all("Insurance Claim", filters={
		"docstatus": 1,
		"status": ["in", ("Submitted", "Acknowledged", "In Review", "Appealed")],
	}, fields=["name", "submitted_on", "claim_date"])
	for claim in claims:
		base = claim.submitted_on or claim.claim_date
		frappe.db.set_value("Insurance Claim", claim.name, "aging_days",
		                    frappe.utils.date_diff(nowdate(), getdate(base)),
		                    update_modified=False)
	frappe.db.commit()


def flag_overdue_lab_cases():
	rows = frappe.get_all("Lab Case", filters={
		"due_date": ["<", nowdate()],
		"status": ["not in", ("Delivered", "Cancelled")]}, fields=["name", "due_date"])
	for row in rows:
		frappe.db.set_value("Lab Case", row.name, {
			"is_late": 1,
			"days_late": frappe.utils.date_diff(nowdate(), row.due_date),
		}, update_modified=False)
	frappe.db.commit()


def expire_waitlist_entries():
	from neo_dentiq.utils.waitlist import expire_stale_entries
	expire_stale_entries()


def licence_expiry_alerts():
	rows = frappe.get_all("Dental Practitioner", filters={
		"license_expiry": ["<=", add_days(nowdate(), 60)], "status": "Active"},
		fields=["name", "license_expiry", "user"])
	for row in rows:
		if getdate(row.license_expiry) < getdate(nowdate()):
			frappe.db.set_value("Dental Practitioner", row.name, "status", "Inactive")
		frappe.publish_realtime("neo_dentiq_alert", {
			"title": "Practitioner licence expiring",
			"message": f"{row.name} licence expires on {row.license_expiry}.",
		})
	frappe.db.commit()


def payment_plan_reminders():
	from neo_dentiq.utils.messaging import log
	rows = frappe.db.sql("""
		select pp.name, pp.patient, ppi.name as row_name, ppi.due_date, ppi.amount
		from `tabPatient Payment Plan` pp
		join `tabPayment Plan Installment` ppi on ppi.parent = pp.name
		where pp.status = 'Active' and ppi.status in ('Pending','Overdue')
		  and ppi.reminder_sent = 0 and ppi.due_date <= %s
	""", add_days(nowdate(), 3), as_dict=True)
	for row in rows:
		try:
			log(row.patient, "Email", "Payment Reminder",
			    f"An installment of {row.amount} is due on {row.due_date}.")
			frappe.db.set_value("Payment Plan Installment", row.row_name,
			                    "reminder_sent", 1, update_modified=False)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Neo Dentiq payment reminder")
	frappe.db.commit()
