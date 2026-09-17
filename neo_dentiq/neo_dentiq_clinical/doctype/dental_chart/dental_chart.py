# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

DECAYED = ("Caries",)
FILLED = ("Restored", "Root Canal Treated", "Crowned", "Veneered")
MISSING_STATUS = ("Missing", "Extracted")


class DentalChart(Document):
	def validate(self):
		self.compute_indices()
		self.last_charted_on = nowdate()

	def build_default_teeth(self):
		"""Seed the odontogram with the correct dentition from Tooth Master."""
		self.teeth = []
		filters = {"dentition": ["in", ["Permanent", "Primary"]]}
		if self.dentition in ("Permanent", "Primary"):
			filters = {"dentition": self.dentition}
		teeth = frappe.get_all(
			"Tooth Master", filters=filters, fields=["name"], order_by="tooth_code"
		)
		for t in teeth:
			self.append("teeth", {"tooth": t.name, "status": "Present", "condition": "Sound"})

	def compute_indices(self):
		"""WHO DMFT index — the standard epidemiological caries measure."""
		decayed = missing = filled = 0
		for row in self.teeth or []:
			if row.status in MISSING_STATUS:
				missing += 1
			elif row.condition in DECAYED:
				decayed += 1
			elif row.condition in FILLED:
				filled += 1
		self.decayed_count = decayed
		self.missing_count = missing
		self.filled_count = filled
		self.dmft_score = decayed + missing + filled

	@frappe.whitelist()
	def set_tooth(self, tooth, **kwargs):
		"""Called from the odontogram widget."""
		row = next((r for r in self.teeth if r.tooth == tooth), None)
		if not row:
			row = self.append("teeth", {"tooth": tooth})
		for key, value in kwargs.items():
			if hasattr(row, key):
				setattr(row, key, value)
		row.last_updated_on = nowdate()
		self.save()
		return row.as_dict()
