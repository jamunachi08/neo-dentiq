# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class PatientCommunication(Document):
	def before_insert(self):
		if not self.patient_name:
			self.patient_name = frappe.db.get_value("Patient", self.patient, "patient_name")

	@frappe.whitelist()
	def resend(self):
		from neo_dentiq.utils.messaging import dispatch
		return dispatch(self)
