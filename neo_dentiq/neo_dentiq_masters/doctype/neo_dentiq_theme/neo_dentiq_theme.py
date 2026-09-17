# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from neo_dentiq.setup.theme_presets import (
	APPOINTMENT_STATUSES, MODULE_COLOURS, PERIO_BANDS, PRESETS, ROLE_COLOURS,
	TOOTH_CONDITIONS, TOOTH_STATUSES,
)

CACHE_KEY = "neo_dentiq_theme"

RADIUS = {"Sharp": "0px", "Soft": "4px", "Rounded": "10px", "Pill": "18px"}
DENSITY = {"Comfortable": "1", "Compact": "0.82"}
INTENSITY = {"Subtle": "0.06", "Balanced": "0.12", "Vivid": "0.2"}
FONTS = {
	"Inter": "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
	"Nunito": "'Nunito', system-ui, -apple-system, 'Segoe UI', sans-serif",
	"Poppins": "'Poppins', system-ui, -apple-system, 'Segoe UI', sans-serif",
	"Source Sans 3": "'Source Sans 3', system-ui, -apple-system, sans-serif",
	"System Default": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
}

SEED_TABLES = {
	"tooth_condition_colours": TOOTH_CONDITIONS,
	"tooth_status_colours": TOOTH_STATUSES,
	"appointment_status_colours": APPOINTMENT_STATUSES,
	"perio_colours": PERIO_BANDS,
	"role_colours": ROLE_COLOURS,
	"module_colours": MODULE_COLOURS,
}

FEATURE_FIELDS = (
	"colourful_sidebar", "gradient_headers", "coloured_status_pills",
	"coloured_workspace_cards", "colour_coded_odontogram", "colour_coded_perio",
	"colour_coded_calendar", "colourful_patient_banner", "animated_transitions",
	"respect_reduced_motion", "tooth_glyphs", "colour_blind_safe",
)

PALETTE_FIELDS = tuple(PRESETS["Clinical Mint"].keys())


class NeoDentiqTheme(Document):
	def validate(self):
		self.seed_tables()
		before = self.get_doc_before_save()
		if self.theme_preset != "Custom" and (
			not before or before.theme_preset != self.theme_preset
		):
			self.apply_preset_values(self.theme_preset)

	def on_update(self):
		frappe.cache().delete_value(CACHE_KEY)
		frappe.publish_realtime("neo_dentiq_theme_changed", self.as_theme())

	# ------------------------------------------------------------
	def seed_tables(self):
		"""Fill any colour table that has never been populated."""
		for field, rows in SEED_TABLES.items():
			if self.get(field):
				continue
			for key, label, colour, text_colour, icon in rows:
				self.append(field, {
					"key": key, "label": label, "colour": colour,
					"text_colour": text_colour, "icon": icon, "is_active": 1,
				})

	def apply_preset_values(self, preset):
		values = PRESETS.get(preset)
		if not values:
			return
		for field, colour in values.items():
			setattr(self, field, colour)

	# ------------------------------------------------------------
	def as_theme(self):
		"""The payload the browser needs: variables, feature flags, colour maps."""
		if not self.enable_theme:
			return {"enabled": False}

		variables = {
			"--ndq-primary": self.primary_colour,
			"--ndq-secondary": self.secondary_colour,
			"--ndq-accent": self.accent_colour,
			"--ndq-success": self.success_colour,
			"--ndq-warning": self.warning_colour,
			"--ndq-danger": self.danger_colour,
			"--ndq-info": self.info_colour,
			"--ndq-bg": self.background_colour,
			"--ndq-surface": self.surface_colour,
			"--ndq-text": self.text_colour,
			"--ndq-muted": self.muted_text_colour,
			"--ndq-border": self.border_colour,
			"--ndq-radius": RADIUS.get(self.corner_radius, "10px"),
			"--ndq-density": DENSITY.get(self.density, "1"),
			"--ndq-tint": INTENSITY.get(self.accent_intensity, "0.12"),
			"--ndq-font": FONTS.get(self.font_family, FONTS["Inter"]),
			"--ndq-primary-soft": _tint(self.primary_colour, 0.12),
			"--ndq-secondary-soft": _tint(self.secondary_colour, 0.12),
			"--ndq-accent-soft": _tint(self.accent_colour, 0.12),
			"--ndq-success-soft": _tint(self.success_colour, 0.14),
			"--ndq-warning-soft": _tint(self.warning_colour, 0.16),
			"--ndq-danger-soft": _tint(self.danger_colour, 0.12),
			"--ndq-gradient": (
				f"linear-gradient(120deg, {self.primary_colour} 0%, "
				f"{self.secondary_colour} 55%, {self.accent_colour} 100%)"
			),
		}

		return {
			"enabled": True,
			"preset": self.theme_preset,
			"colour_mode": self.colour_mode,
			"apply_to_desk": bool(self.apply_to_desk),
			"apply_to_portal": bool(self.apply_to_portal),
			"variables": {k: v for k, v in variables.items() if v},
			"features": {f: bool(self.get(f)) for f in FEATURE_FIELDS},
			"maps": {
				"tooth_condition": _map(self.tooth_condition_colours),
				"tooth_status": _map(self.tooth_status_colours),
				"appointment_status": _map(self.appointment_status_colours),
				"perio": _map(self.perio_colours),
				"role": _map(self.role_colours),
				"module": _map(self.module_colours),
			},
			"custom_css": self.custom_css or "",
		}

	# ------------------------------------------------------------ actions
	@frappe.whitelist()
	def preview_preset(self, preset):
		return PRESETS.get(preset, {})

	@frappe.whitelist()
	def reset_colour_tables(self):
		for field in SEED_TABLES:
			self.set(field, [])
		self.seed_tables()
		self.save()
		return _("Colour tables restored to the shipped defaults.")

	@frappe.whitelist()
	def apply_preset(self, preset):
		self.theme_preset = preset
		self.apply_preset_values(preset)
		self.save()
		return self.as_theme()


def _map(rows):
	return {
		row.key: {
			"colour": row.colour,
			"text": row.text_colour,
			"icon": row.icon,
			"label": row.label or row.key,
		}
		for row in rows or [] if row.is_active
	}


def _tint(hex_colour, alpha):
	"""Return the colour as an rgba string so surfaces can be softly washed."""
	if not hex_colour:
		return ""
	value = hex_colour.lstrip("#")
	if len(value) == 3:
		value = "".join(c * 2 for c in value)
	try:
		r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
	except ValueError:
		return hex_colour
	return f"rgba({r}, {g}, {b}, {alpha})"


@frappe.whitelist(allow_guest=True)
def get_theme():
	"""Cached theme payload, used by the desk boot and the portal."""
	cached = frappe.cache().get_value(CACHE_KEY)
	if cached:
		return cached
	try:
		theme = frappe.get_cached_doc("Neo Dentiq Theme").as_theme()
	except Exception:
		theme = {"enabled": False}
	frappe.cache().set_value(CACHE_KEY, theme, expires_in_sec=3600)
	return theme
