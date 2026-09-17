"""Public online-booking API used by the portal and any external front end."""
import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from neo_dentiq.utils.scheduling import available_slots, find_next_available


@frappe.whitelist(allow_guest=True)
def get_clinics():
	return frappe.get_all("Dental Clinic", filters={"is_active": 1},
	                      fields=["name", "clinic_name", "city", "phone"])


@frappe.whitelist(allow_guest=True)
def get_appointment_types(new_patient=0):
	filters = {"is_online_bookable": 1}
	if int(new_patient or 0):
		filters["allow_new_patients"] = 1
	return frappe.get_all("Appointment Type", filters=filters,
	                      fields=["name", "appointment_type", "default_duration",
	                              "deposit_required"])


@frappe.whitelist(allow_guest=True)
def get_practitioners(clinic=None, speciality=None):
	filters = {"status": "Active", "accepts_online_booking": 1}
	if clinic:
		filters["primary_clinic"] = clinic
	if speciality:
		filters["speciality"] = speciality
	return frappe.get_all("Dental Practitioner", filters=filters,
	                      fields=["name", "practitioner_name", "speciality",
	                              "qualification", "image", "languages",
	                              "default_appointment_duration"])


@frappe.whitelist(allow_guest=True)
def get_slots(practitioner, date, appointment_type=None):
	return available_slots(practitioner, date, appointment_type=appointment_type)


@frappe.whitelist(allow_guest=True)
def get_next_available(clinic=None, appointment_type=None, days=14):
	return find_next_available(clinic=clinic, appointment_type=appointment_type,
	                           days=days)


@frappe.whitelist(allow_guest=True)
def request_appointment(first_name, mobile, appointment_type, appointment_date,
                        appointment_time, practitioner, last_name=None, email=None,
                        clinic=None, reason=None, dob=None, sex=None):
	"""Self-service booking. Creates the patient if they are new."""
	patient = frappe.db.get_value("Patient", {"mobile": mobile}, "name")
	if not patient:
		patient_doc = frappe.get_doc({
			"doctype": "Patient", "first_name": first_name, "last_name": last_name,
			"mobile": mobile, "email": email, "dob": dob or "1990-01-01",
			"sex": sex or "Other", "clinic": clinic,
			"referral_source": "Website Booking"
			if frappe.db.exists("Referral Source", "Website Booking") else None,
		})
		patient_doc.flags.ignore_permissions = True
		patient_doc.insert()
		patient = patient_doc.name

	appointment = frappe.get_doc({
		"doctype": "Dental Appointment", "patient": patient,
		"appointment_type": appointment_type, "appointment_date": appointment_date,
		"appointment_time": appointment_time, "practitioner": practitioner,
		"clinic": clinic, "reason": reason, "status": "Requested",
		"booked_via": "Patient Portal",
	})
	appointment.flags.ignore_permissions = True
	appointment.insert()
	return {"appointment": appointment.name, "patient": patient,
	        "status": appointment.status}


@frappe.whitelist(allow_guest=True)
def join_waitlist(mobile, appointment_type, clinic, priority="Routine",
                  earliest_date=None, latest_date=None):
	patient = frappe.db.get_value("Patient", {"mobile": mobile}, "name")
	if not patient:
		frappe.throw(_("No patient record found for this number."))
	entry = frappe.get_doc({
		"doctype": "Waitlist Entry", "patient": patient,
		"appointment_type": appointment_type, "clinic": clinic, "priority": priority,
		"earliest_date": earliest_date or nowdate(),
		"latest_date": latest_date or add_days(nowdate(), 60),
	})
	entry.flags.ignore_permissions = True
	entry.insert()
	return entry.name
