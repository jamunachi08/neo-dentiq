"""Offline fallback: deterministic local benefit checks, no external service."""
import json

import frappe
from frappe.utils import flt, getdate, nowdate


def build_generic_claim(claim):
	payload = {
		"claim": claim.name,
		"payer": claim.payer,
		"policy_number": claim.policy_number,
		"patient": {
			"id": claim.patient,
			"name": claim.patient_name,
			"dob": str(frappe.db.get_value("Patient", claim.patient, "dob") or ""),
		},
		"provider": {
			"practitioner": claim.practitioner,
			"npi": frappe.db.get_value("Dental Practitioner", claim.practitioner,
			                           "npi_number"),
			"clinic": claim.clinic,
		},
		"lines": [
			{
				"code": line.procedure_code,
				"procedure": line.procedure,
				"tooth": line.tooth,
				"surfaces": line.surfaces,
				"date_of_service": str(line.service_date),
				"diagnosis": line.diagnosis_code,
				"billed": flt(line.billed_amount),
			}
			for line in claim.lines
		],
		"total_billed": flt(claim.total_billed),
	}
	return json.dumps(payload, indent=2)


def local_eligibility(patient, policy_row=None):
	"""Validate policy dates and remaining benefit from local records."""
	rows = frappe.get_all(
		"Patient Insurance Policy",
		filters={"parent": patient, "parenttype": "Patient"},
		fields=["name", "insurance_plan", "payer", "policy_number", "valid_from",
		        "valid_to", "coverage_order"],
	)
	if policy_row:
		rows = [r for r in rows if r.name == policy_row]
	out = []
	for r in rows:
		active = True
		if r.valid_to and getdate(r.valid_to) < getdate(nowdate()):
			active = False
		if r.valid_from and getdate(r.valid_from) > getdate(nowdate()):
			active = False
		from neo_dentiq.utils.insurance import estimate_coverage
		remaining = estimate_coverage.remaining_benefit(patient, frappe._dict(r))
		out.append({
			"policy": r.name,
			"plan": r.insurance_plan,
			"payer": r.payer,
			"status": "Active" if active else "Inactive",
			"remaining_annual_benefit": remaining,
			"source": "local",
		})
		frappe.db.set_value("Patient Insurance Policy", r.name, {
			"eligibility_status": "Active" if active else "Inactive",
			"last_verified_on": frappe.utils.now_datetime(),
		}, update_modified=False)
	return out
