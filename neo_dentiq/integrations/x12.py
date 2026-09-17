"""ANSI ASC X12N 837D dental claim and 270 eligibility enquiry builders."""
import frappe
from frappe.utils import flt, getdate


def _seg(*parts):
	return "*".join(str(p or "") for p in parts) + "~"


def build_837d(claim):
	"""Assemble a minimal but structurally valid 837D transaction set."""
	clinic = frappe.get_cached_doc("Dental Clinic", claim.clinic)
	patient = frappe.get_cached_doc("Patient", claim.patient)
	practitioner = frappe.get_cached_doc("Dental Practitioner", claim.practitioner)
	payer = frappe.get_cached_doc("Insurance Payer", claim.payer)
	now = getdate()

	out = [
		_seg("ST", "837", "0001", "005010X224A2"),
		_seg("BHT", "0019", "00", claim.name, now.strftime("%Y%m%d"), "1200", "CH"),
		# Submitter / receiver
		_seg("NM1", "41", "2", clinic.clinic_name, "", "", "", "", "46", clinic.tax_id),
		_seg("NM1", "40", "2", payer.payer_name, "", "", "", "", "46", payer.payer_id),
		# Billing provider
		_seg("HL", "1", "", "20", "1"),
		_seg("NM1", "85", "2", clinic.clinic_name, "", "", "", "", "XX",
		     practitioner.npi_number),
		_seg("N3", clinic.address),
		_seg("N4", clinic.city, "", "", clinic.country),
		# Subscriber
		_seg("HL", "2", "1", "22", "0"),
		_seg("SBR", "P", "18", "", "", "", "", "", "", "CI"),
		_seg("NM1", "IL", "1", patient.last_name, patient.first_name, "", "", "", "MI",
		     claim.policy_number),
		_seg("DMG", "D8", (patient.dob or "").strftime("%Y%m%d")
		     if hasattr(patient.dob, "strftime") else "",
		     {"Male": "M", "Female": "F"}.get(patient.sex, "U")),
		_seg("NM1", "PR", "2", payer.payer_name, "", "", "", "", "PI", payer.payer_id),
		_seg("CLM", claim.name, flt(claim.total_billed), "", "", "11:B:1", "Y", "A", "Y", "Y"),
	]

	for idx, line in enumerate(claim.lines, start=1):
		out.append(_seg("LX", idx))
		out.append(_seg("SV3", f"AD:{line.procedure_code}", flt(line.billed_amount), "",
		                line.tooth or "", "", 1))
		if line.tooth:
			surfaces = "".join((line.surfaces or "").replace(",", "").upper())
			out.append(_seg("TOO", "JP", line.tooth, surfaces))
		out.append(_seg("DTP", "472", "D8",
		                getdate(line.service_date).strftime("%Y%m%d")))

	out.append(_seg("SE", len(out) + 1, "0001"))
	return "\n".join(out)


def build_270(patient, policy_row=None):
	"""270 eligibility / benefit enquiry."""
	p = frappe.get_cached_doc("Patient", patient)
	rows = frappe.get_all(
		"Patient Insurance Policy",
		filters={"parent": patient, "parenttype": "Patient"},
		fields=["name", "payer", "policy_number"])
	if policy_row:
		rows = [r for r in rows if r.name == policy_row]
	if not rows:
		return ""
	row = rows[0]
	payer = frappe.get_cached_doc("Insurance Payer", row.payer)
	return "\n".join([
		_seg("ST", "270", "0001", "005010X279A1"),
		_seg("BHT", "0022", "13", p.name, getdate().strftime("%Y%m%d"), "1200"),
		_seg("NM1", "PR", "2", payer.payer_name, "", "", "", "", "PI", payer.payer_id),
		_seg("NM1", "IL", "1", p.last_name, p.first_name, "", "", "", "MI",
		     row.policy_number),
		_seg("EQ", "35"),
		_seg("SE", "6", "0001"),
	])


def parse_835(content):
	"""Parse an 835 remittance into Claim Remittance lines."""
	lines, current = [], {}
	for segment in content.replace("\n", "").split("~"):
		parts = segment.split("*")
		if not parts or not parts[0]:
			continue
		if parts[0] == "CLP":
			if current:
				lines.append(current)
			current = {
				"claim": parts[1] if len(parts) > 1 else "",
				"billed_amount": flt(parts[3]) if len(parts) > 3 else 0,
				"paid_amount": flt(parts[4]) if len(parts) > 4 else 0,
				"patient_responsibility": flt(parts[5]) if len(parts) > 5 else 0,
			}
		elif parts[0] == "CAS" and current:
			current["denial_code"] = parts[2] if len(parts) > 2 else ""
			current["adjustment"] = flt(parts[3]) if len(parts) > 3 else 0
	if current:
		lines.append(current)
	return lines
