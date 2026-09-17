# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

PD_SITES = ("pd_db", "pd_b", "pd_mb", "pd_dl", "pd_l", "pd_ml")
BOP_SITES = ("bop_db", "bop_b", "bop_mb", "bop_dl", "bop_l", "bop_ml")


class PeriodontalChart(Document):
	def validate(self):
		self.compute_site_values()
		self.compute_indices()
		if frappe.db.get_single_value("Neo Dentiq Settings", "enable_perio_auto_staging"):
			self.classify()

	def on_submit(self):
		self.push_risk_to_patient()

	# ------------------------------------------------------------ math
	def compute_site_values(self):
		for row in self.readings or []:
			if row.is_missing:
				row.max_pd = 0
				row.cal_max = 0
				continue
			depths = [cint(row.get(f)) for f in PD_SITES]
			row.max_pd = max(depths) if depths else 0
			# CAL = probing depth + recession, taken at the worst site per aspect
			cal_b = max(cint(row.pd_db), cint(row.pd_b), cint(row.pd_mb)) + cint(row.rec_b)
			cal_l = max(cint(row.pd_dl), cint(row.pd_l), cint(row.pd_ml)) + cint(row.rec_l)
			row.cal_max = max(cal_b, cal_l)

	def compute_indices(self):
		total_sites = bleeding = plaque_sites = deep_sites = 0
		pd_sum = cal_sum = present = 0
		for row in self.readings or []:
			if row.is_missing:
				continue
			present += 1
			for f in PD_SITES:
				total_sites += 1
				depth = cint(row.get(f))
				pd_sum += depth
				if depth >= 5:
					deep_sites += 1
			for f in BOP_SITES:
				if row.get(f):
					bleeding += 1
			if row.plaque:
				plaque_sites += 6
			cal_sum += cint(row.cal_max)

		self.teeth_present = present
		self.sites_5mm_plus = deep_sites
		self.bop_percent = flt(bleeding * 100.0 / total_sites, 2) if total_sites else 0
		self.plaque_index_percent = (
			flt(plaque_sites * 100.0 / total_sites, 2) if total_sites else 0
		)
		self.mean_pd = flt(pd_sum / total_sites, 2) if total_sites else 0
		self.mean_cal = flt(cal_sum / present, 2) if present else 0

	# ------------------------------------------------------------ AAP/EFP 2018
	def classify(self):
		"""2018 AAP/EFP world-workshop staging and grading."""
		cals = [cint(r.cal_max) for r in self.readings or [] if not r.is_missing]
		max_cal = max(cals) if cals else 0
		missing_teeth = len([r for r in self.readings or [] if r.is_missing])
		max_pd = max([cint(r.max_pd) for r in self.readings or []] or [0])
		furcation = any((r.furcation or "0") in ("II", "III") for r in self.readings or [])
		mobility = any(cint(r.mobility) >= 2 for r in self.readings or [])

		if max_cal == 0 and self.bop_percent < 10:
			stage = "Health"
		elif max_cal <= 1 and self.bop_percent >= 10:
			stage = "Gingivitis"
		elif max_cal <= 2:
			stage = "Stage I"
		elif max_cal <= 4:
			stage = "Stage II"
		elif max_cal >= 5 and (missing_teeth >= 5 or mobility or self.sites_5mm_plus > 10):
			stage = "Stage IV"
		else:
			stage = "Stage III"

		# Complexity upgrades
		if stage in ("Stage I", "Stage II") and (max_pd >= 6 or furcation):
			stage = "Stage III"
		if stage == "Stage III" and missing_teeth >= 5:
			stage = "Stage IV"

		self.perio_stage = stage

		# Extent
		affected = len([c for c in cals if c >= 3])
		total = len(cals) or 1
		pct = affected * 100.0 / total
		self.extent = "Generalized" if pct > 30 else ("Localized" if pct else "Localized")

		# Grade — primary criterion is bone loss % / age
		modifiers = []
		grade = "Grade B"
		age_years = _patient_age(self.patient)
		if self.bone_loss_percent and age_years:
			ratio = flt(self.bone_loss_percent / age_years, 2)
			self.bone_loss_age_ratio = ratio
			if ratio < 0.25:
				grade = "Grade A"
			elif ratio <= 1.0:
				grade = "Grade B"
			else:
				grade = "Grade C"

		patient = frappe.db.get_value(
			"Patient", self.patient, ["smoking_status", "caries_risk"], as_dict=True
		) or {}
		if patient.get("smoking_status", "").startswith("Current"):
			modifiers.append("Smoker")
			grade = "Grade C" if "Heavy" in patient["smoking_status"] else max(grade, "Grade B")
		if _has_alert(self.patient, "Diabetes"):
			modifiers.append("Diabetes")
			grade = "Grade C"

		self.perio_grade = grade
		self.risk_modifiers = ", ".join(modifiers) or "None"
		if not self.diagnosis:
			self.diagnosis = f"{self.extent} periodontitis, {stage}, {grade}"
		if not self.recommended_therapy:
			self.recommended_therapy = _therapy_for(stage)

	def push_risk_to_patient(self):
		mapping = {
			"Health": "Low", "Gingivitis": "Low", "Stage I": "Low",
			"Stage II": "Moderate", "Stage III": "High", "Stage IV": "High",
		}
		frappe.db.set_value("Patient", self.patient, "perio_risk",
		                    mapping.get(self.perio_stage, "Low"))

	@frappe.whitelist()
	def build_full_mouth(self):
		"""Populate all 32 permanent teeth ready for probing."""
		existing = {r.tooth for r in self.readings or []}
		teeth = frappe.get_all("Tooth Master", filters={"dentition": "Permanent"},
		                       pluck="name", order_by="tooth_code")
		for t in teeth:
			if t not in existing:
				self.append("readings", {"tooth": t})
		self.save()
		return len(self.readings)


def _patient_age(patient):
	from frappe.utils import date_diff, today
	dob = frappe.db.get_value("Patient", patient, "dob")
	return (date_diff(today(), dob) // 365) if dob else 0


def _has_alert(patient, keyword):
	return bool(frappe.db.sql("""
		select 1 from `tabPatient Medical Alert`
		where parent = %s and parenttype = 'Patient'
		  and status != 'Resolved' and medical_alert like %s limit 1
	""", (patient, f"%{keyword}%")))


def _therapy_for(stage):
	return {
		"Health": "Preventive maintenance, 12-month recall.",
		"Gingivitis": "Oral hygiene instruction, supragingival debridement, 6-month recall.",
		"Stage I": "Step 1-2: OHI, professional mechanical plaque removal, subgingival instrumentation.",
		"Stage II": "Step 1-2 therapy with full-mouth subgingival instrumentation; re-evaluate at 3 months.",
		"Stage III": "Step 1-3: non-surgical therapy then access flap / regenerative surgery at residual pockets >=6mm.",
		"Stage IV": "Step 1-4: perio therapy plus occlusal and prosthetic rehabilitation; multidisciplinary plan.",
	}.get(stage, "")
