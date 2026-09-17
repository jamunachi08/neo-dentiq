"""Complete FDI / Universal / Palmer tooth reference, permanent and primary."""

NAMES = {
	1: "Central Incisor", 2: "Lateral Incisor", 3: "Canine",
	4: "First Premolar", 5: "Second Premolar",
	6: "First Molar", 7: "Second Molar", 8: "Third Molar",
}
PRIMARY_NAMES = {
	1: "Central Incisor", 2: "Lateral Incisor", 3: "Canine",
	4: "First Molar", 5: "Second Molar",
}
TYPES = {1: "Incisor", 2: "Incisor", 3: "Canine", 4: "Premolar",
         5: "Premolar", 6: "Molar", 7: "Molar", 8: "Molar"}
PRIMARY_TYPES = {1: "Incisor", 2: "Incisor", 3: "Canine", 4: "Molar", 5: "Molar"}

QUADRANTS = {
	1: ("Upper", "Right"), 2: ("Upper", "Left"),
	3: ("Lower", "Left"), 4: ("Lower", "Right"),
	5: ("Upper", "Right"), 6: ("Upper", "Left"),
	7: ("Lower", "Left"), 8: ("Lower", "Right"),
}

# FDI -> Universal, permanent dentition
UNIVERSAL = {
	"18": "1", "17": "2", "16": "3", "15": "4", "14": "5", "13": "6", "12": "7", "11": "8",
	"21": "9", "22": "10", "23": "11", "24": "12", "25": "13", "26": "14", "27": "15",
	"28": "16",
	"38": "17", "37": "18", "36": "19", "35": "20", "34": "21", "33": "22", "32": "23",
	"31": "24",
	"41": "25", "42": "26", "43": "27", "44": "28", "45": "29", "46": "30", "47": "31",
	"48": "32",
}

# FDI -> Universal letter, primary dentition
UNIVERSAL_PRIMARY = {
	"55": "A", "54": "B", "53": "C", "52": "D", "51": "E",
	"61": "F", "62": "G", "63": "H", "64": "I", "65": "J",
	"75": "K", "74": "L", "73": "M", "72": "N", "71": "O",
	"81": "P", "82": "Q", "83": "R", "84": "S", "85": "T",
}

PALMER_SYMBOL = {1: "UR", 2: "UL", 3: "LL", 4: "LR",
                 5: "UR", 6: "UL", 7: "LL", 8: "LR"}

# Typical root / canal anatomy used to pre-fill endodontic procedures
ROOTS = {
	("Upper", "Incisor"): (1, 1), ("Upper", "Canine"): (1, 1),
	("Lower", "Incisor"): (1, 1), ("Lower", "Canine"): (1, 1),
	("Upper", "Premolar"): (2, 2), ("Lower", "Premolar"): (1, 1),
	("Upper", "Molar"): (3, 4), ("Lower", "Molar"): (2, 3),
}


def _surfaces(tooth_type):
	if tooth_type in ("Incisor", "Canine"):
		return "M,I,D,B,L"
	return "M,O,D,B,L"


def build_teeth():
	rows = []
	for quadrant in (1, 2, 3, 4):
		arch, side = QUADRANTS[quadrant]
		for position in range(1, 9):
			code = f"{quadrant}{position}"
			ttype = TYPES[position]
			roots, canals = ROOTS.get((arch, ttype), (1, 1))
			if position == 8:
				roots, canals = (3, 3) if arch == "Upper" else (2, 3)
			rows.append({
				"doctype": "Tooth Master",
				"tooth_code": code,
				"universal_number": UNIVERSAL[code],
				"palmer_notation": f"{PALMER_SYMBOL[quadrant]}{position}",
				"tooth_name": f"{arch} {side} {NAMES[position]}",
				"dentition": "Permanent",
				"arch": arch,
				"quadrant": quadrant,
				"tooth_type": ttype,
				"side": side,
				"root_count": roots,
				"canal_count": canals,
				"surfaces": _surfaces(ttype),
			})
	for quadrant in (5, 6, 7, 8):
		arch, side = QUADRANTS[quadrant]
		for position in range(1, 6):
			code = f"{quadrant}{position}"
			ttype = PRIMARY_TYPES[position]
			roots, canals = (3, 3) if (arch == "Upper" and ttype == "Molar") else (
				(2, 3) if ttype == "Molar" else (1, 1))
			rows.append({
				"doctype": "Tooth Master",
				"tooth_code": code,
				"universal_number": UNIVERSAL_PRIMARY[code],
				"palmer_notation": f"{PALMER_SYMBOL[quadrant]}{chr(64 + position)}",
				"tooth_name": f"Primary {arch} {side} {PRIMARY_NAMES[position]}",
				"dentition": "Primary",
				"arch": arch,
				"quadrant": quadrant,
				"tooth_type": ttype,
				"side": side,
				"root_count": roots,
				"canal_count": canals,
				"surfaces": _surfaces(ttype),
			})
	return rows


SURFACES = [
	("M", "Mesial", "All"), ("D", "Distal", "All"), ("O", "Occlusal", "Posterior"),
	("I", "Incisal", "Anterior"), ("B", "Buccal", "All"), ("F", "Facial", "Anterior"),
	("L", "Lingual", "All"), ("P", "Palatal", "All"), ("C", "Cervical", "All"),
	("R", "Root", "All"),
]
