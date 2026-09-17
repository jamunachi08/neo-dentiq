# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

DEFAULT_CHECKS = [
	"Operatory surfaces disinfected (barrier + wipe)",
	"Dental unit waterlines flushed 2 minutes",
	"Suction lines flushed with evacuation cleaner",
	"Sharps containers below fill line",
	"Hand hygiene stations stocked",
	"PPE stock adequate (masks, gloves, eyewear, gowns)",
	"Sterilizer function test completed",
	"Clinical waste segregated and sealed",
	"Emergency drug kit in date",
	"Oxygen cylinder pressure adequate",
	"Spillage kit available",
	"Refrigerated medicine temperature logged",
]


class InfectionControlLog(Document):
	def validate(self):
		if not self.checks:
			for item in DEFAULT_CHECKS:
				self.append("checks", {"check_item": item, "status": "Pass"})
		self.overall_result = "Fail" if any(
			c.status == "Fail" for c in self.checks) else "Pass"
