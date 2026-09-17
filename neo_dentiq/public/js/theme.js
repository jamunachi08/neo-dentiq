/**
 * Neo Dentiq theme runtime.
 *
 * Reads the theme payload from boot (desk) or an API call (portal), writes it
 * into CSS custom properties on :root, and toggles a body class per feature so
 * every visual feature can be switched off independently from the settings page.
 */
frappe.provide("neo_dentiq.theme");

const STYLE_ID = "neo-dentiq-theme";
const FEATURE_CLASS = {
	colourful_sidebar: "ndq-colourful-sidebar",
	gradient_headers: "ndq-gradient-headers",
	coloured_status_pills: "ndq-coloured-pills",
	coloured_workspace_cards: "ndq-coloured-cards",
	colour_coded_odontogram: "ndq-colour-odontogram",
	colour_coded_perio: "ndq-colour-perio",
	colour_coded_calendar: "ndq-colour-calendar",
	colourful_patient_banner: "ndq-colour-banner",
	animated_transitions: "ndq-animate",
	tooth_glyphs: "ndq-glyphs",
	colour_blind_safe: "ndq-cb-safe",
};

neo_dentiq.theme.current = null;

neo_dentiq.theme.apply = function (theme) {
	const root = document.documentElement;
	const body = document.body;
	if (!body) return;

	Object.values(FEATURE_CLASS).forEach((cls) => body.classList.remove(cls));
	body.classList.remove("ndq-themed", "ndq-dark");

	const existing = document.getElementById(STYLE_ID);
	if (existing) existing.remove();

	if (!theme || !theme.enabled) {
		neo_dentiq.theme.current = { enabled: false };
		return;
	}

	neo_dentiq.theme.current = theme;
	body.classList.add("ndq-themed");

	Object.entries(theme.variables || {}).forEach(([name, value]) =>
		root.style.setProperty(name, value));

	Object.entries(theme.features || {}).forEach(([feature, on]) => {
		const cls = FEATURE_CLASS[feature];
		if (cls && on) body.classList.add(cls);
	});

	if (theme.colour_mode === "Dark") {
		body.classList.add("ndq-dark");
	} else if (theme.colour_mode === "Follow System"
		&& window.matchMedia("(prefers-color-scheme: dark)").matches) {
		body.classList.add("ndq-dark");
	}

	if (theme.features && theme.features.respect_reduced_motion
		&& window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		body.classList.remove("ndq-animate");
	}

	neo_dentiq.theme.load_font(theme);

	if (theme.custom_css) {
		const style = document.createElement("style");
		style.id = STYLE_ID;
		style.textContent = theme.custom_css;
		document.head.appendChild(style);
	}
};

const FONT_URL = {
	Inter: "Inter:wght@400;500;600;700",
	Nunito: "Nunito:wght@400;600;700;800",
	Poppins: "Poppins:wght@400;500;600;700",
	"Source Sans 3": "Source+Sans+3:wght@400;600;700",
};

neo_dentiq.theme.load_font = function (theme) {
	const family = (theme.variables || {})["--ndq-font"] || "";
	const name = Object.keys(FONT_URL).find((f) => family.includes(f));
	if (!name) return;
	const id = "neo-dentiq-font";
	if (document.getElementById(id)) return;
	const link = document.createElement("link");
	link.id = id;
	link.rel = "stylesheet";
	link.href = `https://fonts.googleapis.com/css2?family=${FONT_URL[name]}&display=swap`;
	document.head.appendChild(link);
};

/** Look up a colour from a named map, with a safe fallback. */
neo_dentiq.theme.colour = function (map, key, fallback) {
	const theme = neo_dentiq.theme.current;
	if (!theme || !theme.enabled) return fallback;
	const entry = (theme.maps || {})[map] || {};
	return (entry[key] && entry[key].colour) || fallback;
};

neo_dentiq.theme.entry = function (map, key) {
	const theme = neo_dentiq.theme.current;
	if (!theme || !theme.enabled) return null;
	return ((theme.maps || {})[map] || {})[key] || null;
};

neo_dentiq.theme.enabled = function (feature) {
	const theme = neo_dentiq.theme.current;
	return !!(theme && theme.enabled && theme.features && theme.features[feature]);
};

neo_dentiq.theme.boot = function () {
	const booted = frappe.boot && frappe.boot.neo_dentiq_theme;
	if (booted) {
		neo_dentiq.theme.apply(booted);
		return;
	}
	frappe.call({
		method: "neo_dentiq.neo_dentiq_masters.doctype.neo_dentiq_theme.neo_dentiq_theme.get_theme",
	}).then((r) => neo_dentiq.theme.apply(r.message));
};

$(document).ready(() => neo_dentiq.theme.boot());

frappe.realtime.on("neo_dentiq_theme_changed", (theme) => neo_dentiq.theme.apply(theme));
