import frappe
from frappe.utils import flt


def on_submit(doc, method=None):
	"""Keep patient lifetime value and appointment production in step."""
	patient = doc.get("neo_dentiq_patient")
	if not patient:
		return
	ltv = flt(frappe.db.sql("""
		select sum(grand_total) from `tabSales Invoice`
		where customer = %s and docstatus = 1
	""", doc.customer)[0][0])
	frappe.db.set_value("Patient", patient, "lifetime_value", ltv, update_modified=False)
	if doc.get("neo_dentiq_appointment"):
		frappe.db.set_value("Dental Appointment", doc.neo_dentiq_appointment,
		                    "production_value", flt(doc.grand_total),
		                    update_modified=False)
