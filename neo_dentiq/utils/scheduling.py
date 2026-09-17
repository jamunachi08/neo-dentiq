"""Slot engine: availability, conflict detection, resource locking."""
import frappe
from frappe import _
from frappe.utils import (add_to_date, cint, get_datetime, get_time, getdate,
                          nowdate, time_diff_in_seconds)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _overlap(a_start, a_end, b_start, b_end):
	return a_start < b_end and b_start < a_end


def _bounds(date, time, minutes):
	start = get_datetime(f"{date} {time}")
	return start, add_to_date(start, minutes=cint(minutes))


def validate_practitioner_licence(practitioner, date):
	if not practitioner:
		return
	row = frappe.db.get_value(
		"Dental Practitioner", practitioner, ["status", "license_expiry"], as_dict=True)
	if not row:
		return
	if row.status == "Inactive":
		frappe.throw(_("{0} is inactive and cannot be booked.").format(practitioner))
	if row.license_expiry and getdate(row.license_expiry) < getdate(date):
		frappe.throw(_(
			"{0}'s professional licence expires on {1}, before this appointment date."
		).format(practitioner, row.license_expiry))


def check_conflicts(appointment):
	"""Guard practitioner, operatory, patient and leave collisions."""
	settings = frappe.get_cached_doc("Neo Dentiq Settings")
	start, end = _bounds(appointment.appointment_date, appointment.appointment_time,
	                     appointment.duration)

	if _on_leave(appointment.practitioner, start, end):
		frappe.throw(_("{0} is marked unavailable during this slot.")
		             .format(appointment.practitioner))

	blocking = ("Cancelled", "No Show", "Rescheduled", "Completed")
	existing = frappe.get_all(
		"Dental Appointment",
		filters={
			"appointment_date": appointment.appointment_date,
			"status": ["not in", blocking],
			"name": ["!=", appointment.name or ""],
		},
		fields=["name", "patient", "patient_name", "practitioner", "operatory",
		        "appointment_time", "duration", "is_overbooked"],
	)
	for other in existing:
		o_start, o_end = _bounds(appointment.appointment_date, other.appointment_time,
		                         other.duration)
		if not _overlap(start, end, o_start, o_end):
			continue
		if other.patient == appointment.patient:
			frappe.throw(_("Patient already has appointment {0} at this time.")
			             .format(other.name))
		if other.practitioner == appointment.practitioner:
			if settings.allow_double_booking or appointment.is_overbooked:
				continue
			if settings.enable_smart_overbooking and _overbook_allowed(other, settings):
				appointment.is_overbooked = 1
				frappe.msgprint(_(
					"Smart overbook: {0} is double-booked against a high no-show-risk "
					"appointment ({1}%)."
				).format(other.patient_name, other.get("no_show_risk") or 0), alert=True)
				continue
			frappe.throw(_("{0} is already booked at this time ({1}).")
			             .format(appointment.practitioner, other.name))
		if appointment.operatory and other.operatory == appointment.operatory:
			frappe.throw(_("Operatory {0} is occupied by {1}.")
			             .format(appointment.operatory, other.name))


def _overbook_allowed(other, settings):
	risk = cint(frappe.db.get_value("Dental Appointment", other.name, "no_show_risk"))
	return risk >= cint(settings.overbook_risk_threshold or 55)


def _on_leave(practitioner, start, end):
	rows = frappe.get_all(
		"Practitioner Unavailability",
		filters={"practitioner": practitioner},
		fields=["from_datetime", "to_datetime"],
	)
	return any(_overlap(start, end, get_datetime(r.from_datetime),
	                    get_datetime(r.to_datetime)) for r in rows)


@frappe.whitelist()
def available_slots(practitioner, date, duration=None, appointment_type=None,
                    operatory=None):
	"""Return bookable start times for a practitioner on a date."""
	settings = frappe.get_cached_doc("Neo Dentiq Settings")
	date = getdate(date)
	duration = cint(duration) or cint(frappe.db.get_value(
		"Appointment Type", appointment_type, "default_duration")) or cint(
		frappe.db.get_value("Dental Practitioner", practitioner,
		                    "default_appointment_duration")) or 30
	granularity = cint(settings.slot_granularity_minutes) or 10

	schedule = frappe.db.get_value("Dental Practitioner", practitioner, "schedule")
	if not schedule:
		return []
	weekday = WEEKDAYS[date.weekday()]
	windows = frappe.get_all(
		"Practitioner Time Slot",
		filters={"parent": schedule, "day": weekday},
		fields=["from_time", "to_time", "operatory", "slot_purpose"],
	)
	if not windows:
		return []

	booked = frappe.get_all(
		"Dental Appointment",
		filters={"appointment_date": date, "practitioner": practitioner,
		         "status": ["not in", ("Cancelled", "No Show", "Rescheduled")]},
		fields=["appointment_time", "duration", "no_show_risk"],
	)
	blocks = [_bounds(date, b.appointment_time, b.duration) for b in booked]
	leaves = frappe.get_all(
		"Practitioner Unavailability", filters={"practitioner": practitioner},
		fields=["from_datetime", "to_datetime"])

	slots = []
	for w in windows:
		if operatory and w.operatory and w.operatory != operatory:
			continue
		cursor = get_datetime(f"{date} {w.from_time}")
		window_end = get_datetime(f"{date} {w.to_time}")
		while add_to_date(cursor, minutes=duration) <= window_end:
			slot_end = add_to_date(cursor, minutes=duration)
			clash = any(_overlap(cursor, slot_end, s, e) for s, e in blocks)
			on_leave = any(_overlap(cursor, slot_end, get_datetime(l.from_datetime),
			                        get_datetime(l.to_datetime)) for l in leaves)
			if not clash and not on_leave and _lead_time_ok(cursor, settings):
				slots.append({
					"time": cursor.strftime("%H:%M:%S"),
					"display": cursor.strftime("%I:%M %p").lstrip("0"),
					"operatory": w.operatory or operatory,
					"purpose": w.slot_purpose,
					"duration": duration,
				})
			cursor = add_to_date(cursor, minutes=granularity)
	return slots


def _lead_time_ok(start, settings):
	from frappe.utils import now_datetime
	lead = cint(settings.min_booking_lead_minutes)
	return time_diff_in_seconds(start, now_datetime()) >= lead * 60


@frappe.whitelist()
def find_next_available(clinic=None, appointment_type=None, duration=30, days=14,
                        practitioner=None):
	"""First-available search across every practitioner in a clinic."""
	from frappe.utils import add_days
	filters = {"status": "Active", "accepts_online_booking": 1}
	if clinic:
		filters["primary_clinic"] = clinic
	if practitioner:
		filters["name"] = practitioner
	practitioners = frappe.get_all("Dental Practitioner", filters=filters, pluck="name")
	out = []
	for offset in range(cint(days)):
		date = add_days(nowdate(), offset)
		for p in practitioners:
			for slot in available_slots(p, date, duration, appointment_type):
				slot["practitioner"] = p
				slot["date"] = str(date)
				out.append(slot)
				break
		if len(out) >= 20:
			break
	return out
