"""Multi-channel patient messaging with templated, localised content."""
import frappe
from frappe.utils import cint, format_datetime, get_datetime, getdate, now_datetime

TEMPLATES = {
	"Appointment Reminder": {
		"English": "Hi {patient}, this is a reminder of your dental appointment on "
		           "{date} at {time} with {practitioner} at {clinic}. "
		           "Reply YES to confirm or call us to reschedule.",
		"Arabic": "مرحباً {patient}، نذكّرك بموعدك في العيادة يوم {date} الساعة {time} "
		          "مع {practitioner} في {clinic}. يرجى الرد بنعم للتأكيد.",
	},
	"Recall": {
		"English": "Hi {patient}, your dental check-up and hygiene visit is due. "
		           "Book online or reply to this message and we will find you a time.",
		"Arabic": "مرحباً {patient}، حان موعد الفحص الدوري وتنظيف الأسنان. "
		          "يرجى الرد لحجز موعد.",
	},
	"Waitlist Offer": {
		"English": "Hi {patient}, a slot has just opened on {date} at {time} with "
		           "{practitioner}. Reply YES within 30 minutes to claim it.",
		"Arabic": "مرحباً {patient}، توفّر موعد يوم {date} الساعة {time} مع "
		          "{practitioner}. يرجى الرد بنعم خلال 30 دقيقة لحجزه.",
	},
	"Payment Reminder": {
		"English": "Hi {patient}, an installment of {amount} on your treatment payment "
		           "plan is due on {date}.",
		"Arabic": "مرحباً {patient}، يستحق قسط بقيمة {amount} من خطة السداد بتاريخ {date}.",
	},
}


def _render(purpose, patient_doc, **kwargs):
	lang = patient_doc.preferred_language if patient_doc.preferred_language in ("English", "Arabic") else "English"
	template = TEMPLATES.get(purpose, {}).get(lang) or TEMPLATES.get(purpose, {}).get("English", "")
	return template.format(patient=patient_doc.first_name, **kwargs)


def log(patient, channel, purpose, message, **refs):
	doc = frappe.get_doc({
		"doctype": "Patient Communication",
		"patient": patient, "channel": channel, "purpose": purpose,
		"message": message, "status": "Queued", "sent_on": now_datetime(),
		**refs,
	}).insert(ignore_permissions=True)
	dispatch(doc)
	return doc.name


def dispatch(doc):
	"""Deliver via the configured provider. Falls back to Frappe email/notification."""
	settings = frappe.get_cached_doc("Neo Dentiq Settings")
	try:
		if doc.channel == "WhatsApp" and settings.whatsapp_enabled:
			from neo_dentiq.integrations.whatsapp import send_whatsapp
			ref = send_whatsapp(doc)
		elif doc.channel == "SMS" and settings.sms_enabled:
			ref = _send_sms(doc)
		elif doc.channel == "Email" and settings.email_enabled:
			ref = _send_email(doc)
		else:
			doc.db_set("status", "Queued")
			return None
		doc.db_set("status", "Sent")
		doc.db_set("provider_message_id", ref or "")
		return ref
	except Exception as exc:
		doc.db_set("status", "Failed")
		doc.db_set("error", str(exc)[:500])
		frappe.log_error(frappe.get_traceback(), "Neo Dentiq messaging")
		return None


def _send_sms(doc):
	from frappe.core.doctype.sms_settings.sms_settings import send_sms
	mobile = frappe.db.get_value("Patient", doc.patient, "mobile")
	send_sms([mobile], frappe.utils.strip_html(doc.message))
	return "sms"


def _send_email(doc):
	email = frappe.db.get_value("Patient", doc.patient, "email")
	if not email:
		raise ValueError("Patient has no email address")
	frappe.sendmail(recipients=[email], subject=doc.subject or doc.purpose,
	                message=doc.message, reference_doctype=doc.doctype,
	                reference_name=doc.name)
	return "email"


def send_appointment_reminder(appointment):
	patient = frappe.get_doc("Patient", appointment.patient)
	message = _render(
		"Appointment Reminder", patient,
		date=frappe.utils.formatdate(appointment.appointment_date, "dd MMM yyyy"),
		time=frappe.utils.format_time(appointment.appointment_time, "hh:mm a"),
		practitioner=appointment.practitioner, clinic=appointment.clinic,
	)
	name = log(patient.name, patient.preferred_contact_method or "Email",
	           "Appointment Reminder", message, appointment=appointment.name)
	frappe.db.set_value("Dental Appointment", appointment.name, {
		"reminder_count": cint(appointment.reminder_count) + 1,
		"last_reminder_on": now_datetime(),
		"confirmation_status": "Sent" if appointment.confirmation_status == "Not Sent"
		else appointment.confirmation_status,
	}, update_modified=False)
	return name


def send_waitlist_offer(entry, appointment):
	patient = frappe.get_doc("Patient", entry.patient)
	message = _render(
		"Waitlist Offer", patient,
		date=frappe.utils.formatdate(appointment.appointment_date, "dd MMM yyyy"),
		time=frappe.utils.format_time(appointment.appointment_time, "hh:mm a"),
		practitioner=appointment.practitioner,
	)
	return log(patient.name, patient.preferred_contact_method or "Email",
	           "Appointment Reminder", message, appointment=appointment.name)


def send_recall(recall):
	patient = frappe.get_doc("Patient", recall.patient)
	message = _render("Recall", patient)
	name = log(patient.name, patient.preferred_contact_method or "Email",
	           "Recall", message, recall=recall.name)
	frappe.db.set_value("Recall Schedule", recall.name, {
		"status": "Contacted",
		"contact_attempts": cint(recall.contact_attempts) + 1,
		"last_contacted_on": now_datetime(),
	}, update_modified=False)
	return name
