"""Idempotent installer for every Neo Dentiq master record.

Safe to re-run: existing documents are skipped, never overwritten, so a site can
be upgraded without losing local edits to fee schedules or protocols.
"""
import frappe
from frappe.utils import flt

from neo_dentiq.setup import master_data as md
from neo_dentiq.setup.tooth_data import SURFACES, build_teeth


def install_all():
	steps = [
		("roles", install_roles),
		("item groups", install_item_groups),
		("teeth", install_teeth),
		("tooth surfaces", install_surfaces),
		("specialities", install_specialities),
		("procedure categories", install_categories),
		("procedure codes", install_procedure_codes),
		("diagnosis codes", install_diagnosis_codes),
		("instrument kits", install_instrument_kits),
		("consumable items", install_consumables),
		("procedures", install_procedures),
		("clinical pathways", install_pathways),
		("medications", install_medications),
		("drug interactions", install_interactions),
		("allergies", install_allergies),
		("medical alerts", install_medical_alerts),
		("appointment types", install_appointment_types),
		("cancellation reasons", install_cancellation_reasons),
		("recall types", install_recall_types),
		("referral sources", install_referral_sources),
		("lab case types", install_lab_case_types),
		("consent templates", install_consent_templates),
		("intake template", install_intake_template),
		("radiograph types", install_radiograph_types),
		("custom fields", install_custom_fields),
		("workflows", install_workflows),
	]
	for label, fn in steps:
		try:
			fn()
			frappe.db.commit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Neo Dentiq install: {label}")
	print("Neo Dentiq master data installed.")


def _insert(doc):
	name = doc.get("__name") or doc.get(_name_field(doc["doctype"]))
	if name and frappe.db.exists(doc["doctype"], name):
		return name
	doc.pop("__name", None)
	d = frappe.get_doc(doc)
	d.flags.ignore_permissions = True
	d.flags.ignore_mandatory = True
	d.insert(ignore_if_duplicate=True)
	return d.name


NAME_FIELDS = {
	"Tooth Master": "tooth_code", "Tooth Surface": "surface_code",
	"Dental Speciality": "speciality_name", "Dental Procedure Category": "category_name",
	"Dental Procedure Code": "code", "Dental Diagnosis Code": "code",
	"Dental Procedure": "procedure_name", "Medication Master": "medication_name",
	"Allergy Master": "allergy_name", "Medical Alert Master": "alert_name",
	"Appointment Type": "appointment_type", "Cancellation Reason": "reason",
	"Recall Type": "recall_type", "Referral Source": "source_name",
	"Lab Case Type": "case_type", "Consent Form Template": "template_name",
	"Instrument Kit": "kit_name", "Radiograph Type": "radiograph_type",
	"Clinical Pathway": "pathway_name", "Patient Intake Template": "template_name",
	"Item Group": "item_group_name", "Item": "item_code", "Role": "role_name",
}


def _name_field(doctype):
	return NAME_FIELDS.get(doctype, "name")


# ------------------------------------------------------------------ steps
def install_roles():
	for role, desc in md.ROLES:
		if frappe.db.exists("Role", role):
			continue
		frappe.get_doc({
			"doctype": "Role", "role_name": role, "desk_access": role != "Patient Portal User",
			"is_custom": 1,
		}).insert(ignore_permissions=True)


def install_item_groups():
	for group in md.ITEM_GROUPS:
		if frappe.db.exists("Item Group", group):
			continue
		frappe.get_doc({
			"doctype": "Item Group", "item_group_name": group,
			"parent_item_group": "All Item Groups", "is_group": 0,
		}).insert(ignore_permissions=True)


def install_teeth():
	for row in build_teeth():
		_insert(row)


def install_surfaces():
	for code, name, applies in SURFACES:
		_insert({"doctype": "Tooth Surface", "surface_code": code,
		         "surface_name": name, "applies_to": applies})


def install_specialities():
	for name, desc in md.SPECIALITIES:
		_insert({"doctype": "Dental Speciality", "speciality_name": name,
		         "description": desc})


def install_categories():
	for name, parent, group, phase, colour in md.CATEGORIES:
		_insert({
			"doctype": "Dental Procedure Category", "category_name": name,
			"parent_dental_procedure_category": parent, "is_group": 0,
			"item_group": group, "default_phase": phase, "colour": colour,
		})


def install_procedure_codes():
	for code, desc, category in md.CDT_CODES:
		_insert({"doctype": "Dental Procedure Code", "code": code,
		         "code_system": "CDT (ADA)", "code_description": desc,
		         "category": category, "is_active": 1})


def install_diagnosis_codes():
	for code, diagnosis, category in md.ICD_CODES:
		_insert({"doctype": "Dental Diagnosis Code", "code": code,
		         "diagnosis": diagnosis, "category": category, "is_active": 1})


def install_instrument_kits():
	for kit, sclass, cycle, items in md.INSTRUMENT_KITS:
		if frappe.db.exists("Instrument Kit", kit):
			continue
		doc = frappe.get_doc({
			"doctype": "Instrument Kit", "kit_name": kit,
			"kit_code": "".join(w[0] for w in kit.split())[:6].upper(),
			"sterilization_class": sclass, "cycle_type": cycle,
			"max_reuse_count": 0,
		})
		for item in items:
			code = _ensure_item(item, "Dental Instruments", "Nos", stock=1)
			doc.append("items", {"item_code": code, "qty": 1})
		doc.insert(ignore_permissions=True)


def _ensure_item(name, group, uom="Nos", stock=1, batch=0, serial=0):
	code = name if len(name) <= 140 else name[:140]
	if frappe.db.exists("Item", code):
		return code
	frappe.get_doc({
		"doctype": "Item", "item_code": code, "item_name": name,
		"item_group": group, "stock_uom": uom, "is_stock_item": stock,
		"has_batch_no": batch, "has_expiry_date": batch,
		"has_serial_no": serial, "is_sales_item": 0 if stock else 1,
		"is_purchase_item": 1, "include_item_in_manufacturing": 0,
	}).insert(ignore_permissions=True)
	return code


def install_consumables():
	for name, group, uom in md.CONSUMABLES:
		batch = group in ("Dental Materials", "Dental Pharmacy", "Dental Implants")
		serial = group == "Dental Implants"
		_ensure_item(name, group, uom, stock=1, batch=1 if batch else 0,
		             serial=1 if serial else 0)


def install_procedures():
	for row in md.PROCEDURES:
		name, category, code, scope, duration, fee, flags = row
		if frappe.db.exists("Dental Procedure", name):
			continue
		doc = frappe.get_doc({
			"doctype": "Dental Procedure",
			"procedure_name": name,
			"procedure_code": code if frappe.db.exists("Dental Procedure Code", code) else None,
			"category": category,
			"tooth_scope": scope,
			"default_duration": duration,
			"cleanup_minutes": 10,
			"standard_rate": fee,
			"abbr": flags.get("abbr"),
			"requires_consent": flags.get("consent", 0),
			"requires_lab_case": flags.get("lab", 0),
			"requires_radiograph": flags.get("radiograph", 0),
			"requires_anaesthesia": flags.get("anaesthesia", 0),
			"is_surgical": flags.get("surgical", 0),
			"default_visits": flags.get("visits", 1),
			"healing_days_before_next": flags.get("healing", 0),
			"warranty_months": flags.get("warranty", 0),
			"instrument_kit": flags.get("kit"),
			"is_active": 1,
		})
		for item, qty in _default_consumables(category).items():
			if frappe.db.exists("Item", item):
				doc.append("consumables", {"item_code": item, "qty": qty})
		doc.insert(ignore_permissions=True)


def _default_consumables(category):
	base = {"Nitrile Gloves (Box)": 0.02, "Face Mask Type IIR (Box)": 0.01,
	        "Disposable Bib": 1, "Saliva Ejector": 1, "Cotton Roll": 4}
	extra = {
		"Restorative": {"Composite Resin A2": 0.2, "Bonding Agent": 0.1,
		                "Etchant Gel 37%": 0.1},
		"Endodontics": {"Gutta Percha Points": 1, "Endodontic Sealer": 0.1,
		                "Calcium Hydroxide Paste": 0.1},
		"Oral Surgery": {"Suture 3-0 Silk": 1, "Articaine 4% with Epinephrine": 2},
		"Implantology": {"Titanium Implant Fixture 4.0x10mm": 1,
		                 "Healing Abutment 4.5mm": 1, "Bone Graft Granules 0.5g": 1,
		                 "Collagen Membrane": 1, "Suture 3-0 Silk": 2},
		"Prosthodontics": {"Impression Material - PVS": 0.3,
		                   "Temporary Crown Material": 0.2},
		"Preventive": {"Fluoride Varnish 5% NaF": 0.2},
	}
	out = dict(base)
	out.update(extra.get(category, {}))
	return out


def install_pathways():
	for name, indication, steps in md.PATHWAYS:
		if frappe.db.exists("Clinical Pathway", name):
			continue
		doc = frappe.get_doc({
			"doctype": "Clinical Pathway", "pathway_name": name,
			"indication": indication, "is_active": 1,
			"evidence_source": "Consensus clinical protocol",
		})
		for step, procedure, description, gap, optional in steps:
			doc.append("steps", {
				"step": step,
				"procedure": procedure if frappe.db.exists("Dental Procedure", procedure) else None,
				"step_description": description, "gap_days": gap,
				"is_optional": optional,
			})
		doc.insert(ignore_permissions=True)
	# link pathways back onto procedures
	for row in md.PROCEDURES:
		name, _, _, _, _, _, flags = row
		if flags.get("pathway") and frappe.db.exists("Clinical Pathway", flags["pathway"]):
			frappe.db.set_value("Dental Procedure", name, "clinical_pathway",
			                    flags["pathway"], update_modified=False)


def install_medications():
	for row in md.MEDICATIONS:
		name, generic, cls, strength, dosage, freq, days, route, flags = row
		if frappe.db.exists("Medication Master", name):
			continue
		item = None
		if route in ("Oral", "Rinse", "Topical", "Submucosal"):
			item = _ensure_item(name, "Dental Pharmacy", "Nos", stock=1, batch=1)
		frappe.get_doc({
			"doctype": "Medication Master", "medication_name": name,
			"generic_name": generic, "drug_class": cls, "item": item,
			"default_strength": strength, "default_dosage": dosage,
			"default_frequency": freq, "default_duration_days": days, "route": route,
			"is_antibiotic": flags.get("antibiotic", 0),
			"is_controlled_substance": flags.get("controlled", 0),
			"pregnancy_category": flags.get("preg", "Unclassified"),
			"is_active": 1,
		}).insert(ignore_permissions=True)


def install_interactions():
	for a, b, severity, effect, management in md.INTERACTIONS:
		if not (frappe.db.exists("Medication Master", a)
		        and frappe.db.exists("Medication Master", b)):
			continue
		if frappe.db.exists("Drug Interaction Rule",
		                    {"medication_a": a, "medication_b": b}):
			continue
		frappe.get_doc({
			"doctype": "Drug Interaction Rule", "medication_a": a, "medication_b": b,
			"severity": severity, "effect": effect, "management": management,
			"is_active": 1, "reference": "Standard dental therapeutics guidance",
		}).insert(ignore_permissions=True)


def install_allergies():
	for name, atype, reaction, critical in md.ALLERGIES:
		_insert({"doctype": "Allergy Master", "allergy_name": name,
		         "allergy_type": atype, "common_reaction": reaction,
		         "is_critical": critical})


def install_medical_alerts():
	for row in md.MEDICAL_ALERTS:
		(name, icd, severity, prophylaxis, bleeding, anaes, vaso, nsaid, clearance,
		 implications, precautions) = row
		_insert({
			"doctype": "Medical Alert Master", "alert_name": name, "icd_code": icd,
			"severity": severity, "requires_antibiotic_prophylaxis": prophylaxis,
			"bleeding_risk": bleeding, "anaesthesia_caution": anaes,
			"avoid_vasoconstrictor": vaso, "avoid_nsaids": nsaid,
			"requires_medical_clearance": clearance,
			"dental_implications": implications, "precautions": precautions,
		})


def install_appointment_types():
	for row in md.APPOINTMENT_TYPES:
		name, duration, colour, online, new_patients, procedure, op_type, intake = row
		_insert({
			"doctype": "Appointment Type", "appointment_type": name,
			"default_duration": duration, "colour": colour,
			"is_online_bookable": online, "allow_new_patients": new_patients,
			"default_procedure": procedure if procedure and frappe.db.exists(
				"Dental Procedure", procedure) else None,
			"requires_operatory_type": op_type,
			"requires_intake_form": intake,
			"intake_form_template": "Standard Medical History" if intake else None,
		})


def install_cancellation_reasons():
	for reason, rtype, no_show, chargeable, release in md.CANCELLATION_REASONS:
		_insert({"doctype": "Cancellation Reason", "reason": reason,
		         "reason_type": rtype, "counts_as_no_show": no_show,
		         "chargeable": chargeable, "release_slot_to_waitlist": release})


def install_recall_types():
	for name, interval, procedure, duration, low, mod, high in md.RECALL_TYPES:
		_insert({
			"doctype": "Recall Type", "recall_type": name,
			"interval_months": interval,
			"default_procedure": procedure if procedure and frappe.db.exists(
				"Dental Procedure", procedure) else None,
			"default_duration": duration, "low_risk_months": low,
			"moderate_risk_months": mod, "high_risk_months": high,
			"reminder_lead_days": 14, "is_active": 1,
		})


def install_referral_sources():
	for name, stype in md.REFERRAL_SOURCES:
		_insert({"doctype": "Referral Source", "source_name": name,
		         "source_type": stype, "is_active": 1})


def install_lab_case_types():
	for name, turnaround, cost, stages in md.LAB_CASE_TYPES:
		_insert({"doctype": "Lab Case Type", "case_type": name,
		         "turnaround_days": turnaround, "default_cost": cost,
		         "stages": stages, "requires_shade": 1})


def install_consent_templates():
	for name, category, body, risks, alternatives in md.CONSENT_TEMPLATES:
		_insert({
			"doctype": "Consent Form Template", "template_name": name,
			"procedure_category": category if category and frappe.db.exists(
				"Dental Procedure Category", category) else None,
			"consent_body": f"<p>{body}</p>",
			"risks": f"<p>{risks}</p>",
			"alternatives": f"<p>{alternatives}</p>",
			"post_op": "<p>Post-operative instructions will be provided in writing "
			           "and explained before you leave the clinic.</p>",
			"require_patient_signature": 1, "require_practitioner_signature": 1,
			"require_guardian_if_minor": 1, "validity_days": 180,
			"version": "1.0", "language": "English", "is_active": 1,
		})


def install_intake_template():
	name = "Standard Medical History"
	if frappe.db.exists("Patient Intake Template", name):
		return
	doc = frappe.get_doc({
		"doctype": "Patient Intake Template", "template_name": name,
		"is_active": 1, "language": "English", "send_before_hours": 48,
	})
	for question, ftype, options, mandatory, maps_to in md.INTAKE_QUESTIONS:
		doc.append("questions", {
			"question": question, "field_type": ftype, "options": options,
			"is_mandatory": mandatory, "maps_to": maps_to,
		})
	doc.insert(ignore_permissions=True)


def install_radiograph_types():
	for name, modality, dose, duration in md.RADIOGRAPH_TYPES:
		_insert({"doctype": "Radiograph Type", "radiograph_type": name,
		         "modality": modality, "effective_dose_msv": dose,
		         "default_duration": duration, "justification_required": 1})


# ------------------------------------------------------------------ ERPNext glue
CUSTOM_FIELDS = {
	"Sales Invoice": [
		("neo_dentiq_patient", "Link", "Patient", "Patient", "customer"),
		("neo_dentiq_clinic", "Link", "Clinic", "Dental Clinic", "neo_dentiq_patient"),
		("neo_dentiq_practitioner", "Link", "Practitioner", "Dental Practitioner",
		 "neo_dentiq_clinic"),
		("neo_dentiq_appointment", "Link", "Appointment", "Dental Appointment",
		 "neo_dentiq_practitioner"),
		("neo_dentiq_zatca_qr", "Small Text", "ZATCA QR", None, "neo_dentiq_appointment"),
	],
	"Sales Invoice Item": [
		("neo_dentiq_tooth", "Link", "Tooth", "Tooth Master", "item_name"),
		("neo_dentiq_procedure_code", "Data", "Procedure Code", None, "neo_dentiq_tooth"),
	],
	"Stock Entry": [
		("neo_dentiq_clinical_procedure", "Link", "Clinical Procedure", "Clinical Procedure",
		 "remarks"),
	],
	"Customer": [
		("neo_dentiq_patient", "Link", "Patient", "Patient", "customer_name"),
	],
	"Item": [
		("neo_dentiq_is_clinical", "Check", "Clinical Item", None, "item_group"),
		("neo_dentiq_udi_di", "Data", "UDI-DI", None, "neo_dentiq_is_clinical"),
	],
	"Purchase Invoice": [
		("neo_dentiq_lab_case", "Link", "Lab Case", "Lab Case", "supplier"),
	],
	"Employee": [
		("neo_dentiq_practitioner", "Link", "Dental Practitioner", "Dental Practitioner",
		 "designation"),
	],
}


def install_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field
	for doctype, fields in CUSTOM_FIELDS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		for fieldname, fieldtype, label, options, insert_after in fields:
			if frappe.db.exists("Custom Field", f"{doctype}-{fieldname}"):
				continue
			create_custom_field(doctype, {
				"fieldname": fieldname, "fieldtype": fieldtype, "label": label,
				"options": options, "insert_after": insert_after,
				"read_only": 0, "allow_on_submit": 0, "print_hide": 1,
			})


WORKFLOWS = [
	{
		"name": "Neo Dentiq Treatment Plan Approval",
		"document_type": "Treatment Plan",
		"state_field": "status",
		"is_active": 1,
		"send_email_alert": 0,
		"states": [
			("Draft", 0, "Dentist", "Blue"),
			("Presented", 1, "Front Desk", "Orange"),
			("Partially Accepted", 1, "Front Desk", "Yellow"),
			("Accepted", 1, "Front Desk", "Green"),
			("Declined", 1, "Front Desk", "Red"),
			("Completed", 1, "Dentist", "Green"),
		],
		"transitions": [
			("Draft", "Present to Patient", "Presented", "Dentist"),
			("Presented", "Accept All", "Accepted", "Front Desk"),
			("Presented", "Partially Accept", "Partially Accepted", "Front Desk"),
			("Presented", "Decline", "Declined", "Front Desk"),
			("Partially Accepted", "Accept Remaining", "Accepted", "Front Desk"),
			("Accepted", "Mark Completed", "Completed", "Dentist"),
		],
	},
	{
		"name": "Neo Dentiq Lab Case Flow",
		"document_type": "Lab Case",
		"state_field": "status",
		"is_active": 1,
		"send_email_alert": 0,
		"states": [
			("Draft", 0, "Dentist", "Blue"),
			("Impression Taken", 0, "Dentist", "Blue"),
			("Sent to Lab", 0, "Front Desk", "Orange"),
			("In Fabrication", 0, "Front Desk", "Orange"),
			("Received", 0, "Front Desk", "Yellow"),
			("Try-in", 0, "Dentist", "Yellow"),
			("Remake", 0, "Dentist", "Red"),
			("Delivered", 0, "Dentist", "Green"),
			("Cancelled", 0, "Neo Dentiq Manager", "Red"),
		],
		"transitions": [
			("Draft", "Take Impression", "Impression Taken", "Dentist"),
			("Impression Taken", "Send to Lab", "Sent to Lab", "Front Desk"),
			("Sent to Lab", "Acknowledge", "In Fabrication", "Front Desk"),
			("In Fabrication", "Receive", "Received", "Front Desk"),
			("Received", "Try-in", "Try-in", "Dentist"),
			("Try-in", "Approve & Deliver", "Delivered", "Dentist"),
			("Try-in", "Request Remake", "Remake", "Dentist"),
			("Remake", "Resend to Lab", "Sent to Lab", "Front Desk"),
		],
	},
	{
		"name": "Neo Dentiq Insurance Claim Flow",
		"document_type": "Insurance Claim",
		"state_field": "status",
		"is_active": 1,
		"send_email_alert": 0,
		"states": [
			("Draft", 0, "Insurance Coordinator", "Blue"),
			("Ready to Submit", 1, "Insurance Coordinator", "Blue"),
			("Submitted", 1, "Insurance Coordinator", "Orange"),
			("In Review", 1, "Insurance Coordinator", "Orange"),
			("Approved", 1, "Insurance Coordinator", "Green"),
			("Partially Approved", 1, "Insurance Coordinator", "Yellow"),
			("Denied", 1, "Insurance Coordinator", "Red"),
			("Appealed", 1, "Insurance Coordinator", "Orange"),
			("Paid", 1, "Neo Dentiq Manager", "Green"),
			("Closed", 1, "Neo Dentiq Manager", "Gray"),
		],
		"transitions": [
			("Draft", "Mark Ready", "Ready to Submit", "Insurance Coordinator"),
			("Ready to Submit", "Submit to Payer", "Submitted", "Insurance Coordinator"),
			("Submitted", "Payer Acknowledged", "In Review", "Insurance Coordinator"),
			("In Review", "Approve", "Approved", "Insurance Coordinator"),
			("In Review", "Partially Approve", "Partially Approved", "Insurance Coordinator"),
			("In Review", "Deny", "Denied", "Insurance Coordinator"),
			("Denied", "Appeal", "Appealed", "Insurance Coordinator"),
			("Approved", "Post Payment", "Paid", "Neo Dentiq Manager"),
			("Partially Approved", "Post Payment", "Paid", "Neo Dentiq Manager"),
			("Paid", "Close", "Closed", "Neo Dentiq Manager"),
		],
	},
]


def install_workflows():
	for wf in WORKFLOWS:
		if frappe.db.exists("Workflow", wf["name"]):
			continue
		for state, _, _, style in wf["states"]:
			if not frappe.db.exists("Workflow State", state):
				frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state,
				                "style": style}).insert(ignore_permissions=True)
		for _, action, _, _ in wf["transitions"]:
			if not frappe.db.exists("Workflow Action Master", action):
				frappe.get_doc({"doctype": "Workflow Action Master",
				                "workflow_action_name": action}).insert(ignore_permissions=True)
		doc = frappe.get_doc({
			"doctype": "Workflow", "workflow_name": wf["name"],
			"document_type": wf["document_type"], "workflow_state_field": wf["state_field"],
			"is_active": wf["is_active"], "send_email_alert": wf["send_email_alert"],
			"override_status": 0,
		})
		for state, doc_status, role, style in wf["states"]:
			doc.append("states", {"state": state, "doc_status": doc_status,
			                      "allow_edit": role, "style": style})
		for from_state, action, to_state, role in wf["transitions"]:
			doc.append("transitions", {"state": from_state, "action": action,
			                           "next_state": to_state, "allowed": role,
			                           "allow_self_approval": 1})
		doc.insert(ignore_permissions=True)


@frappe.whitelist()
def install_demo_clinic(company=None):
	"""Optional starter clinic, operatories, trays and a practitioner schedule."""
	company = company or frappe.defaults.get_defaults().get("company") \
		or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Create a Company in ERPNext first.")

	clinic = "Main Dental Clinic"
	if not frappe.db.exists("Dental Clinic", clinic):
		frappe.get_doc({
			"doctype": "Dental Clinic", "clinic_name": clinic, "company": company,
			"clinic_code": "MDC", "is_active": 1,
		}).insert(ignore_permissions=True)

	for i in range(1, 5):
		name = f"Operatory {i}"
		if not frappe.db.exists("Dental Operatory", name):
			frappe.get_doc({
				"doctype": "Dental Operatory", "operatory_name": name, "clinic": clinic,
				"operatory_type": ["General", "General", "Hygiene", "Surgical"][i - 1],
				"hourly_operating_cost": 120,
			}).insert(ignore_permissions=True)

	schedule = "Standard Weekday Schedule"
	if not frappe.db.exists("Dental Practitioner Schedule", schedule):
		doc = frappe.get_doc({
			"doctype": "Dental Practitioner Schedule", "schedule_name": schedule,
			"clinic": clinic, "is_active": 1,
		})
		for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
			doc.append("time_slots", {"day": day, "from_time": "09:00:00",
			                          "to_time": "13:00:00", "operatory": "Operatory 1"})
			doc.append("time_slots", {"day": day, "from_time": "14:00:00",
			                          "to_time": "18:00:00", "operatory": "Operatory 1"})
		doc.insert(ignore_permissions=True)

	if not frappe.db.exists("Sterilizer", "Autoclave 1"):
		frappe.get_doc({
			"doctype": "Sterilizer", "sterilizer_name": "Autoclave 1", "clinic": clinic,
			"sterilizer_type": "Class B Vacuum Autoclave", "chamber_capacity_litres": 22,
			"bi_test_frequency": "Weekly",
		}).insert(ignore_permissions=True)

	for kit in frappe.get_all("Instrument Kit", pluck="name"):
		prefix = frappe.db.get_value("Instrument Kit", kit, "kit_code") or "KIT"
		for n in range(1, 4):
			code = f"{prefix}-{n:03d}"
			if frappe.db.exists("Instrument Tray", code):
				continue
			frappe.get_doc({
				"doctype": "Instrument Tray", "tray_code": code, "instrument_kit": kit,
				"clinic": clinic, "status": "Dirty / Awaiting Reprocessing",
			}).insert(ignore_permissions=True)

	settings = frappe.get_single("Neo Dentiq Settings")
	settings.default_company = company
	settings.default_clinic = clinic
	settings.default_recall_type = "Routine Check-up Recall"
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	return "Demo clinic installed."
