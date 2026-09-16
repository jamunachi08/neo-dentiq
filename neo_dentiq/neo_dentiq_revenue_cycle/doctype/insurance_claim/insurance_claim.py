# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, date_diff, flt, getdate, now_datetime, nowdate


class InsuranceClaim(Document):
	def validate(self):
		self.compute_totals()
		self.set_deadline()
		self.set_aging()
		self.validate_filing_window()

	def on_submit(self):
		if self.status == "Draft":
			self.status = "Ready to Submit"
			self.db_update()

	# ------------------------------------------------------------
	def compute_totals(self):
		billed = allowed = paid = resp = adj = 0
		for row in self.lines:
			billed += flt(row.billed_amount)
			allowed += flt(row.allowed_amount)
			paid += flt(row.paid_amount)
			resp += flt(row.patient_responsibility)
			adj += flt(row.adjustment)
		self.total_billed = billed
		self.total_allowed = allowed
		self.total_paid = paid
		self.total_patient_responsibility = resp
		self.total_adjustment = adj
		self.outstanding = billed - paid - adj - resp

	def set_deadline(self):
		days = cint(frappe.db.get_value(
			"Insurance Payer", self.payer, "claim_filing_limit_days")) or 90
		base = min([getdate(r.service_date) for r in self.lines] or [getdate(self.claim_date)])
		self.filing_deadline = add_days(base, days)

	def set_aging(self):
		if self.submitted_on:
			self.aging_days = date_diff(nowdate(), getdate(self.submitted_on))
		else:
			self.aging_days = date_diff(nowdate(), getdate(self.claim_date))

	def validate_filing_window(self):
		if self.status in ("Draft", "Ready to Submit") and self.filing_deadline:
			left = date_diff(self.filing_deadline, nowdate())
			if left < 0:
				frappe.msgprint(
					_("Filing deadline passed {0} days ago — this claim will be denied for timely filing.")
					.format(abs(left)), indicator="red", alert=True)
			elif left <= 10:
				frappe.msgprint(
					_("Filing deadline in {0} days.").format(left),
					indicator="orange", alert=True)

	# ------------------------------------------------------------ actions
	@frappe.whitelist()
	def generate_payload(self):
		from neo_dentiq.integrations import build_claim_payload
		payload, mode = build_claim_payload(self)
		self.db_set("edi_payload", payload)
		self.db_set("transmission_mode", mode)
		return {"mode": mode, "payload": payload}

	@frappe.whitelist()
	def mark_submitted(self, reference=None):
		self.db_set("status", "Submitted")
		self.db_set("submitted_on", now_datetime())
		if reference:
			self.db_set("transmission_reference", reference)
		return self.status

	@frappe.whitelist()
	def post_payment(self):
		"""Create the Payment Entry for the payer portion against the Sales Invoice."""
		from neo_dentiq.utils.billing import payer_payment_entry
		pe = payer_payment_entry(self)
		self.db_set("payment_entry", pe)
		self.db_set("status", "Paid" if self.outstanding <= 0 else "Partially Approved")
		return pe

	@frappe.whitelist()
	def create_appeal(self):
		appeal = frappe.copy_doc(self)
		appeal.status = "Appealed"
		appeal.resubmission_count = cint(self.resubmission_count) + 1
		appeal.payer_claim_number = None
		appeal.submitted_on = None
		appeal.insert()
		return appeal.name
