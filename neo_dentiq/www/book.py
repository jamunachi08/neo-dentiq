import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.clinics = frappe.get_all("Dental Clinic", filters={"is_active": 1},
	                                 fields=["name", "clinic_name", "city", "phone"])
	return context
