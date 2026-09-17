# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate, nowdate


class DentalPractitioner(Document):
	def validate(self):
		self.check_licence()

	def check_licence(self):
		if not self.license_expiry:
			return
		days = date_diff(self.license_expiry, nowdate())
		if days < 0:
			self.status = "Inactive"
			frappe.msgprint(
				_("Licence expired {0} days ago. Practitioner set to Inactive and removed "
				  "from the booking pool.").format(abs(days)), indicator="red")
		elif days <= 60:
			frappe.msgprint(
				_("Licence expires in {0} days.").format(days), indicator="orange", alert=True)

	@frappe.whitelist()
	def get_availability(self, date):
		from neo_dentiq.utils.scheduling import available_slots
		return available_slots(self.name, date)
