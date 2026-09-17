# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


class WaitlistEntry(Document):
	def validate(self):
		if not self.latest_date:
			self.latest_date = add_days(nowdate(), 60)
		if self.latest_date and getdate(self.latest_date) < getdate(nowdate()) \
				and self.status == "Active":
			self.status = "Expired"
		if not self.duration:
			self.duration = frappe.db.get_value(
				"Appointment Type", self.appointment_type, "default_duration") or 30

	@frappe.whitelist()
	def convert_to_appointment(self, appointment_date, appointment_time, practitioner=None):
		apt = frappe.get_doc({
			"doctype": "Dental Appointment",
			"patient": self.patient,
			"appointment_type": self.appointment_type,
			"appointment_date": appointment_date,
			"appointment_time": appointment_time,
			"duration": self.duration,
			"practitioner": practitioner or self.practitioner,
			"clinic": self.clinic,
			"filled_from_waitlist": 1,
			"booked_via": "Front Desk",
		}).insert()
		self.db_set("status", "Booked")
		self.db_set("booked_appointment", apt.name)
		return apt.name
