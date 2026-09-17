import frappe
from frappe.utils import flt, nowdate


def on_submit(doc, method=None):
	"""Match receipts against open payment-plan installments."""
	if doc.payment_type != "Receive" or doc.party_type != "Customer":
		return
	patient = frappe.db.get_value("Patient", {"customer": doc.party}, "name")
	if not patient:
		return
	plans = frappe.get_all("Patient Payment Plan",
	                       filters={"patient": patient, "status": "Active"}, pluck="name")
	for plan_name in plans:
		plan = frappe.get_doc("Patient Payment Plan", plan_name)
		remaining = flt(doc.paid_amount)
		changed = False
		for row in plan.installments:
			if row.status in ("Paid", "Waived") or remaining <= 0:
				continue
			if remaining + 0.01 >= flt(row.amount):
				row.status = "Paid"
				row.paid_on = nowdate()
				row.payment_entry = doc.name
				remaining -= flt(row.amount)
				changed = True
		if changed:
			plan.track()
			plan.save(ignore_permissions=True)
