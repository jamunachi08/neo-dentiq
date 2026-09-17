"""WhatsApp Cloud API adapter."""
import frappe
from frappe.utils import strip_html


def send_whatsapp(doc):
	token = frappe.conf.get("whatsapp_token")
	phone_id = frappe.conf.get("whatsapp_phone_id")
	if not (token and phone_id):
		raise ValueError("WhatsApp credentials are not configured in site config")

	mobile = frappe.db.get_value("Patient", doc.patient, "mobile")
	if not mobile:
		raise ValueError("Patient has no mobile number")

	import requests
	response = requests.post(
		f"https://graph.facebook.com/v18.0/{phone_id}/messages",
		headers={"Authorization": f"Bearer {token}",
		         "Content-Type": "application/json"},
		json={
			"messaging_product": "whatsapp",
			"to": mobile.replace(" ", "").replace("+", ""),
			"type": "text",
			"text": {"body": strip_html(doc.message)},
		},
		timeout=20,
	)
	response.raise_for_status()
	data = response.json()
	return (data.get("messages") or [{}])[0].get("id")


@frappe.whitelist(allow_guest=True)
def webhook():
	"""Inbound replies: YES confirms an appointment or claims a waitlist offer."""
	from frappe.utils import now_datetime
	data = frappe.request.get_json(silent=True) or {}
	try:
		entry = data["entry"][0]["changes"][0]["value"]
		message = entry["messages"][0]
		sender = message["from"]
		text = (message.get("text", {}).get("body") or "").strip().lower()
	except (KeyError, IndexError):
		return {"ok": True}

	patient = frappe.db.get_value("Patient", {"mobile": ["like", f"%{sender[-9:]}"]}, "name")
	if not patient:
		return {"ok": True}

	if text in ("yes", "y", "confirm", "نعم"):
		apt = frappe.db.get_value(
			"Dental Appointment",
			{"patient": patient, "status": ["in", ("Scheduled", "Requested")],
			 "appointment_date": [">=", frappe.utils.nowdate()]},
			"name", order_by="appointment_date asc")
		if apt:
			frappe.db.set_value("Dental Appointment", apt, {
				"status": "Confirmed",
				"confirmation_status": "Confirmed by Patient",
			})
			frappe.db.commit()
	return {"ok": True}
