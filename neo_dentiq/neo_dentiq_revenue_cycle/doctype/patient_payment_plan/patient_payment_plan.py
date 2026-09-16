# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, flt, getdate, nowdate


class PatientPaymentPlan(Document):
	def validate(self):
		self.financed_amount = flt(self.total_amount) - flt(self.down_payment)
		if not self.installments:
			self.build_schedule()
		self.track()

	def build_schedule(self):
		n = int(self.number_of_installments or 1)
		principal = flt(self.financed_amount)
		total = principal * (1 + flt(self.interest_percent) / 100.0)
		each = round(total / n, 2)
		date = getdate(self.start_date)
		step = {"Weekly": 7, "Bi-weekly": 14}.get(self.frequency)
		booked = 0
		for i in range(n):
			amount = each if i < n - 1 else round(total - booked, 2)
			booked += amount
			self.append("installments", {"due_date": date, "amount": amount,
			                             "status": "Pending"})
			date = add_days(date, step) if step else add_months(date, 1)

	def track(self):
		paid = sum(flt(r.amount) for r in self.installments if r.status == "Paid")
		self.amount_paid = paid + flt(self.down_payment)
		self.outstanding = flt(self.total_amount) - self.amount_paid
		missed = 0
		nxt = None
		for row in self.installments:
			if row.status == "Pending" and getdate(row.due_date) < getdate(nowdate()):
				row.status = "Overdue"
			if row.status == "Overdue":
				missed += 1
			if row.status in ("Pending", "Overdue") and not nxt:
				nxt = row.due_date
		self.missed_payments = missed
		self.next_due_date = nxt
		if self.outstanding <= 0 and self.status == "Active":
			self.status = "Completed"
		elif missed >= 3 and self.status == "Active":
			self.status = "Defaulted"
