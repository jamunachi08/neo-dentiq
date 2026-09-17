import frappe

from neo_dentiq.setup.install_fixtures import install_all


def before_install():
	"""Roles must exist before DocType permissions are imported."""
	from neo_dentiq.setup.master_data import ROLES

	for role, _description in ROLES:
		if frappe.db.exists("Role", role):
			continue
		frappe.get_doc({
			"doctype": "Role", "role_name": role,
			"desk_access": role != "Patient Portal User", "is_custom": 1,
		}).insert(ignore_permissions=True)
	frappe.db.commit()


def after_install():
	install_all()
	_set_defaults()
	frappe.db.commit()
	print("\nNeo Dentiq installed. Next: open Neo Dentiq Settings, set the default Company "
	      "and Clinic, then run 'Install Demo Clinic' if you want starter operatories.\n")


def after_migrate():
	install_all()
	frappe.db.commit()


def _set_defaults():
	company = frappe.db.get_value("Company", {}, "name")
	if not company:
		return
	settings = frappe.get_single("Neo Dentiq Settings")
	if not settings.default_company:
		settings.default_company = company
		settings.default_currency = frappe.db.get_value("Company", company, "default_currency")
		settings.default_price_list = "Standard Selling"
		settings.flags.ignore_mandatory = True
		settings.save(ignore_permissions=True)
