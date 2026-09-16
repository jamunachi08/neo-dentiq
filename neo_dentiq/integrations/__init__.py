"""Payer, e-invoice and messaging integrations.

Every integration is a thin, swappable adapter. The regime is chosen in
Neo Dentiq Settings, so the same Insurance Claim document can be filed as an
X12 837D transaction in the US, a FHIR bundle through NPHIES in Saudi
Arabia, or exported for manual portal upload anywhere else.
"""
import frappe


def build_claim_payload(claim):
	regime = frappe.db.get_single_value("Neo Dentiq Settings", "insurance_regime")
	if regime == "X12 (US)":
		from neo_dentiq.integrations.x12 import build_837d
		return build_837d(claim), "X12 837D"
	if regime == "NPHIES (Saudi Arabia)":
		from neo_dentiq.integrations.nphies import build_claim_bundle
		return build_claim_bundle(claim), "NPHIES FHIR"
	from neo_dentiq.integrations.generic import build_generic_claim
	return build_generic_claim(claim), "Manual"


def eligibility_request(patient, policy_row=None):
	regime = frappe.db.get_single_value("Neo Dentiq Settings", "insurance_regime")
	if regime == "NPHIES (Saudi Arabia)":
		from neo_dentiq.integrations.nphies import check_eligibility
		return check_eligibility(patient, policy_row)
	if regime == "X12 (US)":
		from neo_dentiq.integrations.x12 import build_270
		return {"status": "Payload ready", "payload": build_270(patient, policy_row)}
	from neo_dentiq.integrations.generic import local_eligibility
	return local_eligibility(patient, policy_row)
