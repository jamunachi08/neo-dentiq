# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


class ConsentRecord(Document):
	def validate(self):
		self.pull_template()
		self.set_status()

	def pull_template(self):
		if self.consent_body or not self.consent_template:
			return
		tpl = frappe.get_doc("Consent Form Template", self.consent_template)
		parts = [tpl.consent_body]
		for label, body in (("Risks", tpl.risks), ("Alternatives", tpl.alternatives),
		                    ("Post-operative Care", tpl.post_op)):
			if body:
				parts.append(f"<h5>{label}</h5>{body}")
		self.consent_body = "".join(parts)
		if tpl.validity_days:
			self.valid_till = add_days(getdate(self.consent_date), tpl.validity_days)

	def set_status(self):
		if self.withdrawn_on:
			self.status = "Withdrawn"
		elif self.valid_till and getdate(self.valid_till) < getdate(nowdate()):
			self.status = "Expired"
		elif self.patient_signature:
			self.status = "Signed"
			if not self.signed_ip:
				self.signed_ip = frappe.local.request_ip
		else:
			self.status = "Draft"
