import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Please sign in to see your dental record.", frappe.PermissionError)
	context.no_cache = 1
	return context
