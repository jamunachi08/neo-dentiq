"""NPHIES (Saudi Arabia) FHIR R4 adapters for eligibility, pre-auth and claims.

Endpoint, client certificate and licence identifiers are read from site config
(`nphies_base_url`, `nphies_license_id`) so no credentials live in the app.
"""
import json
import uuid

import frappe
from frappe.utils import flt, getdate, nowdate


def _ref(resource, rid):
	return {"reference": f"{resource}/{rid}"}


def _patient_resource(patient):
	p = frappe.get_cached_doc("Patient", patient)
	return {
		"resourceType": "Patient",
		"id": p.name,
		"identifier": [{
			"system": "http://nphies.sa/identifier/iqama",
			"value": p.national_id,
		}],
		"name": [{"text": p.patient_name, "family": p.last_name,
		          "given": [p.first_name]}],
		"gender": (p.sex or "").lower(),
		"birthDate": str(p.dob or ""),
		"telecom": [{"system": "phone", "value": p.mobile}],
	}


def build_claim_bundle(claim):
	items = []
	for idx, line in enumerate(claim.lines, start=1):
		entry = {
			"sequence": idx,
			"productOrService": {"coding": [{
				"system": "http://nphies.sa/terminology/CodeSystem/oral-health-op",
				"code": line.procedure_code or "",
				"display": line.procedure,
			}]},
			"servicedDate": str(line.service_date),
			"unitPrice": {"value": flt(line.billed_amount), "currency": "SAR"},
			"net": {"value": flt(line.billed_amount), "currency": "SAR"},
		}
		if line.tooth:
			entry["bodySite"] = {"coding": [{
				"system": "http://terminology.hl7.org/CodeSystem/FDI-oral-region",
				"code": str(line.tooth),
			}]}
		if line.surfaces:
			entry["subSite"] = [{"coding": [{"code": s.strip()}
			                                for s in line.surfaces.split(",") if s.strip()]}]
		items.append(entry)

	bundle = {
		"resourceType": "Bundle",
		"id": str(uuid.uuid4()),
		"type": "message",
		"timestamp": frappe.utils.now(),
		"entry": [
			{"resource": {
				"resourceType": "MessageHeader",
				"eventCoding": {
					"system": "http://nphies.sa/terminology/CodeSystem/ksa-message-events",
					"code": "claim-request",
				},
			}},
			{"resource": _patient_resource(claim.patient)},
			{"resource": {
				"resourceType": "Claim",
				"id": claim.name,
				"status": "active",
				"type": {"coding": [{
					"system": "http://terminology.hl7.org/CodeSystem/claim-type",
					"code": "oral",
				}]},
				"use": "claim",
				"patient": _ref("Patient", claim.patient),
				"created": nowdate(),
				"insurer": {"identifier": {"value": frappe.db.get_value(
					"Insurance Payer", claim.payer, "payer_id")}},
				"priority": {"coding": [{"code": "normal"}]},
				"insurance": [{
					"sequence": 1, "focal": True,
					"identifier": {"value": claim.policy_number},
				}],
				"item": items,
				"total": {"value": flt(claim.total_billed), "currency": "SAR"},
			}},
		],
	}
	return json.dumps(bundle, indent=2, ensure_ascii=False)


def check_eligibility(patient, policy_row=None):
	"""CoverageEligibilityRequest. Falls back to the local check when offline."""
	base = frappe.conf.get("nphies_base_url")
	if not base:
		from neo_dentiq.integrations.generic import local_eligibility
		result = local_eligibility(patient, policy_row)
		for r in result:
			r["source"] = "local (NPHIES endpoint not configured)"
		return result

	payload = {
		"resourceType": "CoverageEligibilityRequest",
		"status": "active",
		"purpose": ["benefits", "validation"],
		"patient": _ref("Patient", patient),
		"created": frappe.utils.now(),
	}
	try:
		import requests
		response = requests.post(
			f"{base}/CoverageEligibilityRequest", json=payload,
			timeout=20, headers={"Content-Type": "application/fhir+json"},
		)
		response.raise_for_status()
		return response.json()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "NPHIES eligibility")
		from neo_dentiq.integrations.generic import local_eligibility
		return local_eligibility(patient, policy_row)


def build_preauth_bundle(preauth):
	claim_like = frappe._dict({
		"name": preauth.name, "patient": preauth.patient,
		"payer": preauth.payer, "policy_number": preauth.policy_number,
		"total_billed": preauth.total_requested,
		"lines": [frappe._dict({
			"procedure_code": frappe.db.get_value(
				"Dental Procedure", l.procedure, "procedure_code"),
			"procedure": l.procedure, "tooth": l.tooth, "surfaces": None,
			"service_date": nowdate(), "billed_amount": l.requested_amount,
		}) for l in preauth.lines],
	})
	bundle = json.loads(build_claim_bundle(claim_like))
	for entry in bundle["entry"]:
		if entry["resource"].get("resourceType") == "Claim":
			entry["resource"]["use"] = "preauthorization"
	return json.dumps(bundle, indent=2, ensure_ascii=False)
