# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate

from neo_dentiq.utils.insurance import estimate_coverage

ACCEPTED = ("Accepted", "Scheduled", "In Progress", "Completed")


class TreatmentPlan(Document):
	def validate(self):
		self.set_fees()
		self.apply_insurance_estimate()
		self.compute_totals()
		self.set_status()
		self.validate_alternatives()

	def on_submit(self):
		self.status = "Presented"
		self.presented_on = now_datetime()
		self.presented_by = frappe.session.user
		self.db_update()

	# ------------------------------------------------------------
	def set_fees(self):
		for row in self.items:
			if not row.fee:
				row.fee = flt(
					frappe.db.get_value("Dental Procedure", row.procedure, "standard_rate")
				)
			if not row.sequence:
				row.sequence = row.idx

	def apply_insurance_estimate(self):
		policy = _primary_policy(self.patient)
		remaining = None
		if policy:
			remaining = estimate_coverage.remaining_benefit(self.patient, policy)
			self.remaining_annual_benefit = remaining
		for row in self.items:
			if not policy:
				row.coverage_percent = 0
				row.insurance_estimate = 0
				row.patient_portion = flt(row.fee) * flt(row.qty or 1)
				continue
			est = estimate_coverage.for_procedure(
				policy=policy, procedure=row.procedure,
				fee=flt(row.fee) * flt(row.qty or 1), patient=self.patient,
			)
			row.coverage_percent = est["coverage_percent"]
			row.insurance_estimate = est["insurance_estimate"]
			row.patient_portion = est["patient_portion"]
			row.preauth_required = est["preauth_required"]

	def compute_totals(self):
		total = accepted = ins = portion = 0
		for row in self.items:
			line = flt(row.fee) * flt(row.qty or 1)
			total += line
			ins += flt(row.insurance_estimate)
			portion += flt(row.patient_portion)
			if row.status in ACCEPTED:
				accepted += line
		if self.discount_percent:
			factor = (100 - flt(self.discount_percent)) / 100.0
			total *= factor
			portion *= factor
		self.total_fee = total
		self.accepted_fee = accepted
		self.total_insurance_estimate = ins
		self.total_patient_portion = portion
		self.acceptance_percent = flt(accepted * 100.0 / total, 2) if total else 0

	def set_status(self):
		if self.docstatus == 0:
			self.status = "Draft"
			return
		statuses = {row.status for row in self.items}
		if statuses and statuses <= {"Completed", "Void"}:
			self.status = "Completed"
		elif statuses & {"In Progress", "Scheduled"}:
			self.status = "In Progress"
		elif statuses == {"Declined"}:
			self.status = "Declined"
		elif self.acceptance_percent >= 100:
			self.status = "Accepted"
		elif self.acceptance_percent > 0:
			self.status = "Partially Accepted"
		elif self.presented_on:
			self.status = "Presented"

	def validate_alternatives(self):
		groups = {}
		for row in self.items:
			if not row.alternative_group:
				continue
			if row.status in ACCEPTED:
				groups.setdefault(row.alternative_group, []).append(row.idx)
		for group, rows in groups.items():
			if len(rows) > 1:
				frappe.throw(
					_("Alternative group {0}: only one option may be accepted (rows {1}).")
					.format(group, ", ".join(map(str, rows)))
				)

	# ------------------------------------------------------------ actions
	@frappe.whitelist()
	def accept_all(self):
		for row in self.items:
			if row.status == "Proposed":
				row.status = "Accepted"
		self.decision_on = now_datetime()
		self.save()
		return self.status

	@frappe.whitelist()
	def create_payment_plan(self, installments=None, down_payment=None):
		installments = int(installments or self.installments or 6)
		down = flt(down_payment or self.down_payment)
		plan = frappe.get_doc({
			"doctype": "Patient Payment Plan",
			"patient": self.patient,
			"treatment_plan": self.name,
			"clinic": self.clinic,
			"start_date": nowdate(),
			"total_amount": self.total_patient_portion,
			"down_payment": down,
			"number_of_installments": installments,
			"status": "Draft",
		})
		plan.insert()
		self.db_set("payment_plan", plan.name)
		return plan.name

	@frappe.whitelist()
	def create_preauthorization(self):
		rows = [r for r in self.items if r.preauth_required and r.status in ACCEPTED]
		if not rows:
			frappe.throw(_("No accepted procedures require pre-authorization."))
		policy = _primary_policy(self.patient)
		pa = frappe.get_doc({
			"doctype": "Insurance Pre Authorization",
			"patient": self.patient,
			"payer": policy.payer,
			"insurance_plan": policy.insurance_plan,
			"policy_number": policy.policy_number,
			"treatment_plan": self.name,
			"practitioner": self.practitioner,
			"narrative": f"Pre-authorization requested from treatment plan {self.name}.",
		})
		for r in rows:
			pa.append("lines", {
				"procedure": r.procedure, "tooth": r.tooth,
				"requested_amount": flt(r.fee) * flt(r.qty or 1),
			})
		pa.insert()
		return pa.name

	@frappe.whitelist()
	def schedule_next_phase(self):
		"""Return the next unscheduled accepted item so the front desk can book it."""
		for row in sorted(self.items, key=lambda r: (r.phase, r.sequence or r.idx)):
			if row.status == "Accepted" and not row.scheduled_appointment:
				return {
					"treatment_plan_item": row.name,
					"procedure": row.procedure,
					"tooth": row.tooth,
					"duration": frappe.db.get_value(
						"Dental Procedure", row.procedure, "default_duration") or 30,
				}
		return None


def _primary_policy(patient):
	rows = frappe.get_all(
		"Patient Insurance Policy",
		filters={"parent": patient, "parenttype": "Patient", "coverage_order": "Primary"},
		fields=["insurance_plan", "payer", "policy_number", "name", "benefit_used_ytd"],
		limit=1,
	)
	return frappe._dict(rows[0]) if rows else None
