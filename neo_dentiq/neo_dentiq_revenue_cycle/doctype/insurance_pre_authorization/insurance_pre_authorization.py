# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, flt, nowdate


class InsurancePreAuthorization(Document):
	def validate(self):
		self.total_requested = sum(flt(r.requested_amount) for r in self.lines)
		self.total_approved = sum(flt(r.approved_amount) for r in self.lines)
		if self.status in ("Submitted", "In Review"):
			self.days_pending = date_diff(nowdate(), self.request_date)
		if self.lines and self.status not in ("Draft", "Submitted", "In Review"):
			statuses = {r.status for r in self.lines}
			if statuses == {"Approved"}:
				self.status = "Approved"
			elif "Approved" in statuses:
				self.status = "Partially Approved"
			elif statuses == {"Denied"}:
				self.status = "Denied"
