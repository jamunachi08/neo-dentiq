"""Prescription safety: interactions, allergies, conditions, duplication."""
import frappe
from frappe.utils import cint

SEVERITY_RANK = {"Minor": 1, "Moderate": 2, "Severe": 3, "Contraindicated": 4}


def run_safety_check(patient, medications):
	medications = [m for m in medications if m]
	messages, worst = [], 0

	worst = max(worst, _allergy_conflicts(patient, medications, messages))
	worst = max(worst, _interactions(patient, medications, messages))
	worst = max(worst, _condition_conflicts(patient, medications, messages))
	worst = max(worst, _duplicate_therapy(medications, messages))
	_pregnancy(patient, medications, messages)

	status = "Clear"
	if worst >= 4:
		status = "Blocked"
	elif worst >= 1:
		status = "Warnings"
	if not medications:
		status = "Not Run"
	return {"status": status, "messages": messages, "severity": worst}


def _allergy_conflicts(patient, medications, messages):
	worst = 0
	allergies = frappe.get_all(
		"Patient Allergy", filters={"parent": patient, "parenttype": "Patient"},
		fields=["allergy", "severity", "reaction"])
	for med in medications:
		info = frappe.db.get_value(
			"Medication Master", med, ["drug_class", "generic_name"], as_dict=True) or {}
		for a in allergies:
			needle = (a.allergy or "").lower()
			haystack = " ".join(filter(None, [
				med.lower(), (info.get("drug_class") or "").lower(),
				(info.get("generic_name") or "").lower()]))
			if needle and needle in haystack:
				rank = 4 if a.severity in ("Severe", "Anaphylaxis") else 3
				worst = max(worst, rank)
				messages.append(
					f"<b>ALLERGY — {a.severity}:</b> patient is allergic to {a.allergy}"
					f"{' (' + a.reaction + ')' if a.reaction else ''}. {med} is contraindicated.")
	return worst


def _interactions(patient, medications, messages):
	worst = 0
	current = frappe.get_all(
		"Patient Medication",
		filters={"parent": patient, "parenttype": "Patient", "is_current": 1},
		pluck="medication")
	pool = list(set(medications + current))
	rules = frappe.get_all(
		"Drug Interaction Rule",
		filters={"is_active": 1,
		         "medication_a": ["in", pool]},
		fields=["medication_a", "medication_b", "severity", "effect", "management"])
	rules += frappe.get_all(
		"Drug Interaction Rule",
		filters={"is_active": 1, "medication_b": ["in", pool]},
		fields=["medication_a", "medication_b", "severity", "effect", "management"])
	seen = set()
	for rule in rules:
		if not rule.medication_b:
			continue
		pair = tuple(sorted([rule.medication_a, rule.medication_b]))
		if pair in seen or not (pair[0] in pool and pair[1] in pool):
			continue
		if not (pair[0] in medications or pair[1] in medications):
			continue
		seen.add(pair)
		rank = SEVERITY_RANK.get(rule.severity, 2)
		worst = max(worst, rank)
		messages.append(
			f"<b>INTERACTION — {rule.severity}:</b> {rule.medication_a} + "
			f"{rule.medication_b}. {rule.effect}"
			f"{' Management: ' + rule.management if rule.management else ''}")
	return worst


def _condition_conflicts(patient, medications, messages):
	worst = 0
	alerts = frappe.get_all(
		"Patient Medical Alert",
		filters={"parent": patient, "parenttype": "Patient", "status": ["!=", "Resolved"]},
		pluck="medical_alert")
	if not alerts:
		return 0
	flags = frappe.get_all(
		"Medical Alert Master", filters={"name": ["in", alerts]},
		fields=["name", "avoid_nsaids", "bleeding_risk", "avoid_vasoconstrictor"])
	nsaid_block = [f.name for f in flags if f.avoid_nsaids]
	bleeding = [f.name for f in flags if f.bleeding_risk]
	for med in medications:
		info = frappe.db.get_value(
			"Medication Master", med, ["drug_class", "is_antibiotic"], as_dict=True) or {}
		cls = (info.get("drug_class") or "").lower()
		if nsaid_block and "nsaid" in cls:
			worst = max(worst, 3)
			messages.append(
				f"<b>CONDITION:</b> {med} is an NSAID; avoid with {', '.join(nsaid_block)}.")
		if bleeding and "anticoag" in cls:
			worst = max(worst, 3)
			messages.append(
				f"<b>CONDITION:</b> {med} increases bleeding risk with {', '.join(bleeding)}.")
	return worst


def _duplicate_therapy(medications, messages):
	classes = {}
	for med in medications:
		cls = frappe.db.get_value("Medication Master", med, "drug_class")
		if cls:
			classes.setdefault(cls, []).append(med)
	worst = 0
	for cls, meds in classes.items():
		if len(meds) > 1:
			worst = max(worst, 2)
			messages.append(
				f"<b>DUPLICATE THERAPY:</b> {', '.join(meds)} are all {cls}.")
	return worst


def _pregnancy(patient, medications, messages):
	row = frappe.db.get_value("Patient", patient,
	                          ["is_pregnant", "pregnancy_week"], as_dict=True) or {}
	if not row.get("is_pregnant"):
		return
	for med in medications:
		cat = frappe.db.get_value("Medication Master", med, "pregnancy_category")
		if cat in ("D", "X"):
			messages.append(
				f"<b>PREGNANCY — Category {cat}:</b> {med} should not be prescribed "
				f"(week {row.get('pregnancy_week') or '?'}).")


@frappe.whitelist()
def check(patient, medications):
	import json
	if isinstance(medications, str):
		medications = json.loads(medications)
	return run_safety_check(patient, medications)


@frappe.whitelist()
def prophylaxis_required(patient):
	"""Antibiotic prophylaxis flag per AHA / NICE infective-endocarditis guidance."""
	rows = frappe.db.sql("""
		select mam.name from `tabPatient Medical Alert` pma
		join `tabMedical Alert Master` mam on mam.name = pma.medical_alert
		where pma.parent = %s and pma.parenttype = 'Patient'
		  and pma.status != 'Resolved' and mam.requires_antibiotic_prophylaxis = 1
	""", patient, as_dict=True)
	return {"required": bool(rows), "conditions": [r.name for r in rows],
	        "regimen": "Amoxicillin 2 g PO 30-60 min pre-op "
	                   "(clindamycin 600 mg if penicillin-allergic)" if rows else None}
