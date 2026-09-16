# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class RecallSchedule(Document):
	def validate(self):
		self.apply_risk_interval()
		if self.status == "Due" and self.due_date \
				and getdate(self.due_date) < getdate(nowdate()):
			self.status = "Overdue"

	def apply_risk_interval(self):
		if self.risk_adjusted or not self.recall_type:
			return
		rt = frappe.get_cached_doc("Recall Type", self.recall_type)
		risk = frappe.db.get_value("Patient", self.patient, "caries_risk") or "Low"
		months = {
			"Low": rt.low_risk_months, "Moderate": rt.moderate_risk_months,
			"High": rt.high_risk_months, "Extreme": rt.high_risk_months,
		}.get(risk) or rt.interval_months
		self.interval_months = months
		self.risk_adjusted = 1
