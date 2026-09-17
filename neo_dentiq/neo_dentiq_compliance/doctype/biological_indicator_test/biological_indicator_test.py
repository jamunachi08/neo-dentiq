# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class BiologicalIndicatorTest(Document):
	def on_update(self):
		if not self.sterilization_cycle:
			return
		mapping = {"Negative (Pass)": "Pass", "Positive (Fail)": "Fail", "Pending": "Pending"}
		result = mapping.get(self.result, "Pending")
		cycle = frappe.get_doc("Sterilization Cycle", self.sterilization_cycle)
		if cycle.docstatus == 1 and result == "Fail" and cycle.cycle_result != "Fail":
			cycle.db_set("biological_indicator_result", "Fail")
			cycle.db_set("cycle_result", "Fail")
			cycle.trigger_recall()
			cycle.update_trays()
