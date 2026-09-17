import frappe


def _user_clinics(user):
	practitioner = frappe.db.get_value("Dental Practitioner", {"user": user},
	                                   "primary_clinic")
	return [practitioner] if practitioner else []


def patient_query(user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return ""
	portal_patient = frappe.db.get_value("Patient", {"user": user}, "name")
	if portal_patient:
		return f"`tabPatient`.name = {frappe.db.escape(portal_patient)}"
	clinics = _user_clinics(user)
	if clinics:
		joined = ", ".join(frappe.db.escape(c) for c in clinics)
		return f"`tabPatient`.clinic in ({joined})"
	return ""


def appointment_query(user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return ""
	portal_patient = frappe.db.get_value("Patient", {"user": user}, "name")
	if portal_patient:
		return f"`tabDental Appointment`.patient = {frappe.db.escape(portal_patient)}"
	return ""


def patient_has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return True
	if doc.user and doc.user == user:
		return ptype in ("read", "write")
	return True


def _is_privileged(user):
	roles = set(frappe.get_roles(user))
	return bool(roles & {"System Manager", "Neo Dentiq Manager", "Administrator"})
