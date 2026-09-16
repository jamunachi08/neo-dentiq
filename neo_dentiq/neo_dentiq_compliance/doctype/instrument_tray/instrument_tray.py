# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class InstrumentTray(Document):
	def validate(self):
		if self.sterile_until and getdate(self.sterile_until) < getdate(nowdate()):
			self.is_expired = 1
			if self.status == "Available (Sterile)":
				self.status = "Dirty / Awaiting Reprocessing"
		else:
			self.is_expired = 0

	@property
	def is_usable(self):
		return self.status == "Available (Sterile)" and not self.is_expired \
			and self.last_cycle_result == "Pass"
