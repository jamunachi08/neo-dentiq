# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

INDICATORS = ("cavitated_lesions", "radiographic_lesions", "white_spots",
              "restorations_last_3_years")
RISK_FACTORS = ("frequent_snacking", "sugary_drinks", "visible_plaque",
                "deep_pits_fissures", "dry_mouth", "orthodontic_appliance",
                "recreational_drug_use", "exposed_roots")
PROTECTIVE = ("fluoridated_water", "fluoride_toothpaste_2x", "fluoride_varnish_6mo",
              "chlorhexidine_use", "xylitol_use", "sealants_present", "adequate_saliva")


class CariesRiskAssessment(Document):
	def validate(self):
		self.score()

	def on_update(self):
		frappe.db.set_value("Patient", self.patient, "caries_risk", self.risk_level)

	def score(self):
		"""CAMBRA balance: disease indicators dominate, protective factors offset."""
		indicators = sum(1 for f in INDICATORS if self.get(f))
		risks = sum(1 for f in RISK_FACTORS if self.get(f))
		protect = sum(1 for f in PROTECTIVE if self.get(f))
		raw = indicators * 3 + risks * 2 - protect
		self.risk_score = raw

		if self.cavitated_lesions and self.dry_mouth:
			level = "Extreme"
		elif indicators >= 1:
			level = "High" if raw >= 4 else "Moderate"
		elif raw >= 6:
			level = "High"
		elif raw >= 2:
			level = "Moderate"
		else:
			level = "Low"
		self.risk_level = level

		self.recommended_recall_months = {
			"Low": 12, "Moderate": 6, "High": 3, "Extreme": 3
		}[level]
		self.recommended_protocol = {
			"Low": "Fluoride toothpaste 2x daily. Bitewings every 24-36 months.",
			"Moderate": "Fluoride toothpaste 2x daily, fluoride varnish 2x/year, xylitol. Bitewings every 12-24 months.",
			"High": "5000 ppm fluoride toothpaste, varnish every 3 months, chlorhexidine 0.12% one week per month, sealants. Bitewings every 6-12 months. Saliva test.",
			"Extreme": "5000 ppm fluoride, calcium phosphate paste, saliva stimulation, chlorhexidine, dietary counselling, 3-month recall. Bitewings every 6 months.",
		}[level]
