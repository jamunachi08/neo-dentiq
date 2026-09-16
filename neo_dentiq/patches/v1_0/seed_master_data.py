import frappe

from neo_dentiq.setup.install_fixtures import install_all


def execute():
	install_all()
	frappe.db.commit()
