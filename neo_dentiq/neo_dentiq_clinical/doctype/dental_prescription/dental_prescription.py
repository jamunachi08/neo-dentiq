# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

from neo_dentiq.utils.drug_safety import run_safety_check


class DentalPrescription(Document):
	def validate(self):
		self.set_quantities()
		self.safety_check()

	def on_submit(self):
		if self.dispense_at_clinic:
			self.dispense()

	def set_quantities(self):
		for row in self.items:
			if row.quantity:
				continue
			per_day = {
				"Once a day": 1, "Twice a day": 2, "Thrice a day": 3,
				"Four times a day": 4, "Every 4 hours": 6,
				"Every 6 hours": 4, "Every 8 hours": 3,
			}.get(row.frequency, 2)
			row.quantity = per_day * (row.duration_days or 5)

	def safety_check(self):
		if not frappe.db.get_single_value("Neo Dentiq Settings", "enable_drug_interaction_check"):
			self.interaction_status = "Not Run"
			return
		result = run_safety_check(self.patient, [r.medication for r in self.items])
		self.flags.safety_result = result
		self.interaction_status = result["status"]
		if result["status"] == "Blocked":
			block = frappe.db.get_single_value("Neo Dentiq Settings", "block_on_severe_interaction")
			if block and not self.override_reason:
				frappe.throw(
					_("Prescription blocked.<br><br>{0}<br><br>Record a clinical override reason to proceed.")
					.format("<br>".join(result["messages"]))
				)
		elif result["messages"]:
			frappe.msgprint("<br>".join(result["messages"]),
			                title=_("Medication Safety"), indicator="orange")

	def dispense(self):
		from neo_dentiq.utils.billing import dispense_medications
		se = dispense_medications(self)
		if se:
			self.db_set("stock_entry", se)
			self.db_set("dispensed", 1)

	@frappe.whitelist()
	def check_safety(self):
		return run_safety_check(self.patient, [r.medication for r in self.items])
