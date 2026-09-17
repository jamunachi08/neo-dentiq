# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate, nowdate


class LabCase(Document):
	def validate(self):
		self.set_due_date()
		self.build_stages()
		self.track_lateness()
		self.count_remakes()

	def set_due_date(self):
		if self.due_date or not (self.sent_date and self.case_type):
			return
		days = frappe.db.get_value("Lab Case Type", self.case_type, "turnaround_days") or 7
		self.due_date = add_days(getdate(self.sent_date), days)

	def build_stages(self):
		if self.stages or not self.case_type:
			return
		raw = frappe.db.get_value("Lab Case Type", self.case_type, "stages") or ""
		for stage in [s.strip() for s in raw.split(",") if s.strip()]:
			self.append("stages", {"stage": stage, "status": "Pending"})

	def track_lateness(self):
		if self.due_date and self.status not in ("Delivered", "Cancelled"):
			late = date_diff(nowdate(), self.due_date)
			self.is_late = 1 if late > 0 else 0
			self.days_late = max(late, 0)
		elif self.due_date and self.received_date:
			late = date_diff(self.received_date, self.due_date)
			self.is_late = 1 if late > 0 else 0
			self.days_late = max(late, 0)

	def count_remakes(self):
		self.remake_count = len([s for s in self.stages if s.status == "Rejected"])

	def on_update(self):
		if self.status == "Delivered" and self.lab_cost and not self.purchase_invoice:
			frappe.msgprint(
				"Lab case delivered. Create the Purchase Invoice against the lab supplier "
				"to book the lab cost.", alert=True,
			)
