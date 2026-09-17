import frappe

from neo_dentiq.neo_dentiq_masters.doctype.neo_dentiq_theme.neo_dentiq_theme import get_theme


def boot_session(bootinfo):
	"""Ship the theme with the desk boot so there is no flash of unstyled desk."""
	try:
		bootinfo.neo_dentiq_theme = get_theme()
	except Exception:
		bootinfo.neo_dentiq_theme = {"enabled": False}

	practitioner = frappe.db.get_value(
		"Dental Practitioner", {"user": frappe.session.user},
		["name", "practitioner_name", "primary_clinic", "practitioner_type"],
		as_dict=True)
	if practitioner:
		bootinfo.neo_dentiq_practitioner = practitioner

	bootinfo.neo_dentiq_clinic = frappe.db.get_single_value(
		"Neo Dentiq Settings", "default_clinic")


def website_context(context):
	context.neo_dentiq_theme = get_theme()
	return context
