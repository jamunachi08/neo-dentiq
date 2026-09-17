"""Colour presets for Neo Dentiq.

Each preset is a complete palette. Dentistry is a visual, reassuring speciality —
these lean bright and clean rather than the grey of generic ERP software — but the
whole theme is switchable and every individual feature can be turned off.
"""

PRESETS = {
	"Clinical Mint": {
		"primary_colour": "#0D9488",
		"secondary_colour": "#2563EB",
		"accent_colour": "#F472B6",
		"success_colour": "#16A34A",
		"warning_colour": "#F59E0B",
		"danger_colour": "#DC2626",
		"info_colour": "#0EA5E9",
		"background_colour": "#F6FBFA",
		"surface_colour": "#FFFFFF",
		"text_colour": "#0F172A",
		"muted_text_colour": "#64748B",
		"border_colour": "#D7E9E6",
	},
	"Coral Smile": {
		"primary_colour": "#E11D48",
		"secondary_colour": "#F97316",
		"accent_colour": "#8B5CF6",
		"success_colour": "#15803D",
		"warning_colour": "#D97706",
		"danger_colour": "#B91C1C",
		"info_colour": "#0891B2",
		"background_colour": "#FFF7F5",
		"surface_colour": "#FFFFFF",
		"text_colour": "#1C1917",
		"muted_text_colour": "#78716C",
		"border_colour": "#F5D9D3",
	},
	"Sunrise Ortho": {
		"primary_colour": "#F59E0B",
		"secondary_colour": "#EC4899",
		"accent_colour": "#14B8A6",
		"success_colour": "#65A30D",
		"warning_colour": "#EA580C",
		"danger_colour": "#DC2626",
		"info_colour": "#3B82F6",
		"background_colour": "#FFFBEB",
		"surface_colour": "#FFFFFF",
		"text_colour": "#1F2937",
		"muted_text_colour": "#78716C",
		"border_colour": "#FDE9B8",
	},
	"Deep Ocean": {
		"primary_colour": "#1D4ED8",
		"secondary_colour": "#0891B2",
		"accent_colour": "#7C3AED",
		"success_colour": "#059669",
		"warning_colour": "#D97706",
		"danger_colour": "#E11D48",
		"info_colour": "#0EA5E9",
		"background_colour": "#F4F8FF",
		"surface_colour": "#FFFFFF",
		"text_colour": "#0F172A",
		"muted_text_colour": "#64748B",
		"border_colour": "#D6E4FB",
	},
	"Berry Bright": {
		"primary_colour": "#7C3AED",
		"secondary_colour": "#DB2777",
		"accent_colour": "#22D3EE",
		"success_colour": "#16A34A",
		"warning_colour": "#F59E0B",
		"danger_colour": "#E11D48",
		"info_colour": "#6366F1",
		"background_colour": "#FBF7FF",
		"surface_colour": "#FFFFFF",
		"text_colour": "#1E1B4B",
		"muted_text_colour": "#6B7280",
		"border_colour": "#E6D9FB",
	},
	"Midnight Clinic": {
		"primary_colour": "#2DD4BF",
		"secondary_colour": "#60A5FA",
		"accent_colour": "#F472B6",
		"success_colour": "#4ADE80",
		"warning_colour": "#FBBF24",
		"danger_colour": "#F87171",
		"info_colour": "#38BDF8",
		"background_colour": "#0B1220",
		"surface_colour": "#131D31",
		"text_colour": "#E2E8F0",
		"muted_text_colour": "#94A3B8",
		"border_colour": "#24324D",
	},
}

# (key, label, colour, text colour, icon)
TOOTH_CONDITIONS = [
	("Sound", "Sound", "#FFFFFF", "#0F172A", ""),
	("Caries", "Caries", "#DC2626", "#FFFFFF", "C"),
	("Restored", "Restored", "#2563EB", "#FFFFFF", "R"),
	("Root Canal Treated", "Root canal treated", "#D97706", "#FFFFFF", "E"),
	("Crowned", "Crowned", "#7C3AED", "#FFFFFF", "Cr"),
	("Veneered", "Veneered", "#0891B2", "#FFFFFF", "V"),
	("Fractured", "Fractured", "#BE123C", "#FFFFFF", "F"),
	("Abraded", "Abraded", "#A16207", "#FFFFFF", "A"),
	("Discoloured", "Discoloured", "#78716C", "#FFFFFF", "D"),
	("Mobile", "Mobile", "#EA580C", "#FFFFFF", "M"),
	("Watch", "Watch", "#CA8A04", "#FFFFFF", "W"),
]

TOOTH_STATUSES = [
	("Present", "Present", "#FFFFFF", "#0F172A", ""),
	("Missing", "Missing", "#CBD5E1", "#475569", "X"),
	("Extracted", "Extracted", "#94A3B8", "#FFFFFF", "X"),
	("Unerupted", "Unerupted", "#E2E8F0", "#475569", "U"),
	("Impacted", "Impacted", "#FB923C", "#FFFFFF", "!"),
	("Implant", "Implant", "#0F766E", "#FFFFFF", "I"),
	("Pontic", "Pontic", "#6366F1", "#FFFFFF", "P"),
	("Primary Retained", "Primary retained", "#F9A8D4", "#3F0F2C", "p"),
]

APPOINTMENT_STATUSES = [
	("Requested", "Requested", "#A78BFA", "#FFFFFF", ""),
	("Scheduled", "Scheduled", "#3B82F6", "#FFFFFF", ""),
	("Confirmed", "Confirmed", "#0EA5E9", "#FFFFFF", ""),
	("Arrived", "Arrived", "#14B8A6", "#FFFFFF", ""),
	("In Operatory", "In operatory", "#8B5CF6", "#FFFFFF", ""),
	("In Progress", "In progress", "#6366F1", "#FFFFFF", ""),
	("Completed", "Completed", "#16A34A", "#FFFFFF", ""),
	("Cancelled", "Cancelled", "#94A3B8", "#FFFFFF", ""),
	("No Show", "No show", "#DC2626", "#FFFFFF", ""),
	("Rescheduled", "Rescheduled", "#F59E0B", "#FFFFFF", ""),
]

PERIO_BANDS = [
	("healthy", "1-3 mm — healthy", "#ECFDF5", "#065F46", ""),
	("moderate", "4-5 mm — moderate", "#FEF3C7", "#92400E", ""),
	("deep", "6 mm and above — deep", "#FEE2E2", "#991B1B", ""),
	("bleeding", "Bleeding on probing", "#DC2626", "#FFFFFF", ""),
]

ROLE_COLOURS = [
	("Neo Dentiq Manager", "Practice manager", "#7C3AED", "#FFFFFF", "shield"),
	("Dentist", "Dentist", "#0D9488", "#FFFFFF", "health"),
	("Dental Hygienist", "Hygienist", "#16A34A", "#FFFFFF", "leaf"),
	("Front Desk", "Front desk", "#2563EB", "#FFFFFF", "calendar"),
	("Insurance Coordinator", "Insurance", "#F59E0B", "#FFFFFF", "money"),
	("Sterilization Officer", "Sterilisation", "#E11D48", "#FFFFFF", "shield"),
	("Patient Portal User", "Patient", "#EC4899", "#FFFFFF", "user"),
]

MODULE_COLOURS = [
	("Neo Dentiq Front Desk", "Front desk", "#2563EB", "#FFFFFF", "calendar"),
	("Neo Dentiq Clinical", "Clinical", "#0D9488", "#FFFFFF", "health"),
	("Neo Dentiq Revenue Cycle", "Revenue cycle", "#F59E0B", "#FFFFFF", "money"),
	("Neo Dentiq Compliance", "Compliance", "#E11D48", "#FFFFFF", "shield"),
	("Neo Dentiq Setup", "Setup", "#7C3AED", "#FFFFFF", "setting"),
]
