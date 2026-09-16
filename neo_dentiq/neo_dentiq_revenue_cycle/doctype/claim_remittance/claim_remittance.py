# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ClaimRemittance(Document):
	def validate(self):
		self.total_paid = sum(flt(r.paid_amount) for r in self.lines)

	def on_submit(self):
		self.apply_to_claims()

	def apply_to_claims(self):
		for row in self.lines:
			claim = frappe.get_doc("Insurance Claim", row.insurance_claim)
			for line in claim.lines:
				if flt(line.paid_amount):
					continue
				line.allowed_amount = flt(row.allowed_amount)
				line.paid_amount = flt(row.paid_amount)
				line.adjustment = flt(row.adjustment)
				line.denial_code = row.denial_code
				line.line_status = "Paid" if flt(row.paid_amount) else "Denied"
				break
			claim.compute_totals()
			claim.status = "Paid" if claim.outstanding <= 0 else "Partially Approved"
			claim.db_update()
			for line in claim.lines:
				line.db_update()
		self.db_set("status", "Posted")
