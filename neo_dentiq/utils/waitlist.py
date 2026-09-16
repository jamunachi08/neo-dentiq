"""Auto-backfill cancelled slots from the waitlist."""
import frappe
from frappe.utils import cint, get_datetime, getdate, now_datetime


def offer_slot(appointment):
	apt = frappe.get_doc("Dental Appointment", appointment)
	candidates = rank_candidates(apt)
	if not candidates:
		return 0
	from neo_dentiq.utils.messaging import send_waitlist_offer
	sent = 0
	for entry in candidates[:3]:
		send_waitlist_offer(entry, apt)
		frappe.db.set_value("Waitlist Entry", entry.name, {
			"status": "Offered",
			"offered_on": now_datetime(),
			"offer_count": cint(entry.offer_count) + 1,
		})
		sent += 1
	frappe.db.commit()
	return sent


def rank_candidates(apt):
	"""Best-fit ordering: priority, arrival feasibility, duration fit, waiting time."""
	entries = frappe.get_all(
		"Waitlist Entry",
		filters={"status": "Active", "clinic": apt.clinic,
		         "earliest_date": ["<=", apt.appointment_date],
		         "latest_date": [">=", apt.appointment_date]},
		fields=["name", "patient", "patient_name", "priority", "duration",
		        "practitioner", "preferred_days", "preferred_time_from",
		        "preferred_time_to", "can_come_within_minutes", "offer_count",
		        "creation", "appointment_type"],
	)
	weekday = getdate(apt.appointment_date).strftime("%A")
	scored = []
	for e in entries:
		if cint(e.duration) > cint(apt.duration):
			continue
		if e.preferred_days and weekday not in e.preferred_days:
			continue
		if e.preferred_time_from and str(apt.appointment_time) < str(e.preferred_time_from):
			continue
		if e.preferred_time_to and str(apt.appointment_time) > str(e.preferred_time_to):
			continue
		score = {"Emergency": 300, "Urgent": 200, "Routine": 100}.get(e.priority, 100)
		if e.practitioner == apt.practitioner:
			score += 40
		if getdate(apt.appointment_date) == getdate():
			score += cint(e.can_come_within_minutes or 0) and 30 or 0
		score -= cint(e.offer_count) * 15
		days_waiting = (now_datetime() - get_datetime(e.creation)).days
		score += min(days_waiting, 30)
		e["score"] = score
		scored.append(frappe._dict(e))
	return sorted(scored, key=lambda x: -x.score)


def expire_stale_entries():
	from frappe.utils import nowdate
	frappe.db.sql("""
		update `tabWaitlist Entry` set status = 'Expired'
		where status in ('Active','Offered') and latest_date < %s
	""", nowdate())
	frappe.db.commit()
