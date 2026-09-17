"""Benefit estimation: coverage %, frequency limits, annual maximum, waiting period."""
import frappe
from frappe.utils import add_months, cint, flt, getdate, nowdate


def for_procedure(policy, procedure, fee, patient):
	plan = frappe.get_cached_doc("Insurance Plan", policy.insurance_plan)
	rule = _match_rule(plan, procedure)
	coverage = flt(rule.coverage_percent) if rule else 0
	preauth = bool(rule.requires_preauth) if rule else False

	if rule and rule.waiting_period_months and _within_waiting_period(policy, rule):
		coverage = 0

	if rule and rule.frequency_limit and _frequency_exhausted(patient, procedure, rule):
		coverage = 0

	estimate = flt(fee) * coverage / 100.0

	remaining = remaining_benefit(patient, policy)
	if remaining is not None:
		estimate = min(estimate, max(remaining, 0))

	if rule and rule.annual_limit:
		estimate = min(estimate, flt(rule.annual_limit))

	if plan.network_tier == "Out-of-Network":
		estimate *= 0.8

	return {
		"coverage_percent": coverage,
		"insurance_estimate": round(estimate, 2),
		"patient_portion": round(flt(fee) - estimate, 2),
		"preauth_required": 1 if preauth or (
			plan.get("requires_preauth_above") and fee > flt(plan.requires_preauth_above)
		) else 0,
	}


def _match_rule(plan, procedure):
	"""Most-specific rule wins: exact procedure, then category, then ancestors."""
	category = frappe.db.get_value("Dental Procedure", procedure, "category")
	exact = [r for r in plan.coverage_rules if r.procedure == procedure]
	if exact:
		return exact[0]
	by_cat = [r for r in plan.coverage_rules if r.procedure_category == category]
	if by_cat:
		return by_cat[0]
	ancestors = _ancestors(category)
	for anc in ancestors:
		match = [r for r in plan.coverage_rules if r.procedure_category == anc]
		if match:
			return match[0]
	return None


def _ancestors(category):
	out = []
	node = category
	guard = 0
	while node and guard < 10:
		node = frappe.db.get_value(
			"Dental Procedure Category", node, "parent_dental_procedure_category")
		if node:
			out.append(node)
		guard += 1
	return out


def _within_waiting_period(policy, rule):
	valid_from = frappe.db.get_value(
		"Patient Insurance Policy", policy.get("name"), "valid_from")
	if not valid_from:
		return False
	eligible = add_months(getdate(valid_from), cint(rule.waiting_period_months))
	return getdate(nowdate()) < eligible


def _frequency_exhausted(patient, procedure, rule):
	"""Parse limits like '2 per year' or '1 per 5 years per tooth'."""
	text = (rule.frequency_limit or "").lower()
	if "per" not in text:
		return False
	parts = text.split("per")
	try:
		allowed = int("".join(c for c in parts[0] if c.isdigit()) or 1)
	except ValueError:
		allowed = 1
	window = parts[1].strip()
	months = 12
	if "year" in window:
		digits = "".join(c for c in window if c.isdigit())
		months = 12 * (int(digits) if digits else 1)
	elif "month" in window:
		digits = "".join(c for c in window if c.isdigit())
		months = int(digits) if digits else 1
	since = add_months(getdate(nowdate()), -months)
	used = frappe.db.count("Clinical Procedure", {
		"patient": patient, "procedure": procedure, "docstatus": 1,
		"procedure_date": [">=", since],
	})
	return used >= allowed


def remaining_benefit(patient, policy):
	plan = frappe.db.get_value(
		"Insurance Plan", policy.insurance_plan,
		["annual_maximum", "benefit_year_start"], as_dict=True) or {}
	if not plan.get("annual_maximum"):
		return None
	year_start = f"{getdate(nowdate()).year}-01-01"
	used = flt(frappe.db.sql("""
		select sum(total_paid) from `tabInsurance Claim`
		where patient = %s and docstatus = 1 and claim_date >= %s
		  and status in ('Approved','Partially Approved','Paid','Closed')
	""", (patient, year_start))[0][0])
	return flt(plan["annual_maximum"]) - used


@frappe.whitelist()
def verify_eligibility(patient, policy_row=None):
	"""Real-time eligibility hook.

	Ships with a deterministic local check; point `eligibility_endpoint` at a
	clearinghouse (X12 270/271) or NPHIES to make it live.
	"""
	from neo_dentiq.integrations import eligibility_request
	return eligibility_request(patient, policy_row)
