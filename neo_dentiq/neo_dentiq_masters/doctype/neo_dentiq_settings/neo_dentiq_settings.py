# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class NeoDentiqSettings(Document):
	def validate(self):
		if self.slot_granularity_minutes and self.slot_granularity_minutes < 5:
			self.slot_granularity_minutes = 5

	@frappe.whitelist()
	def run_setup_wizard(self):
		from neo_dentiq.setup.install_fixtures import install_all
		install_all()
		return "Master data installed."
