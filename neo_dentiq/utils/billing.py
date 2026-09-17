"""ERPNext accounting bridge: invoices, payments, dispensing."""
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def _settings():
	return frappe.get_cached_doc("Neo Dentiq Settings")


def _customer(patient):
	customer = frappe.db.get_value("Patient", patient, "customer")
	if not customer:
		frappe.throw(_("Patient {0} has no linked Customer.").format(patient))
	return customer


def _base_invoice(patient, clinic, appointment=None):
	s = _settings()
	si = frappe.new_doc("Sales Invoice")
	si.customer = _customer(patient)
	si.company = frappe.db.get_value("Dental Clinic", clinic, "company") or s.default_company
	si.posting_date = nowdate()
	si.due_date = nowdate()
	si.neo_dentiq_patient = patient
	si.neo_dentiq_clinic = clinic
	if appointment:
		si.neo_dentiq_appointment = appointment
	si.cost_center = frappe.db.get_value("Dental Clinic", clinic, "cost_center") \
		or s.default_cost_center
	price_list = frappe.db.get_value("Dental Clinic", clinic, "price_list") \
		or s.default_price_list
	if price_list:
		si.selling_price_list = price_list
	return si


def invoice_for_procedure(procedure):
	item = frappe.db.get_value("Dental Procedure", procedure.procedure, "item")
	if not item:
		return None
	si = _base_invoice(procedure.patient, procedure.clinic, procedure.appointment)
	si.neo_dentiq_practitioner = procedure.practitioner
	si.append("items", {
		"item_code": item,
		"qty": 1,
		"rate": flt(procedure.rate),
		"income_account": frappe.db.get_value("Dental Clinic", procedure.clinic,
		                                      "income_account") or _settings().default_income_account,
		"description": _line_description(procedure),
	})
	for row in procedure.consumables:
		if not row.is_billable:
			continue
		si.append("items", {"item_code": row.item_code, "qty": flt(row.qty),
		                    "rate": flt(row.rate)})
	si.insert(ignore_permissions=True)
	si.submit()
	_split_insurance(si, procedure)
	return si.name


def _line_description(procedure):
	bits = [procedure.procedure]
	if procedure.tooth:
		bits.append(f"tooth {procedure.tooth}")
	if procedure.surfaces:
		bits.append(f"surfaces {procedure.surfaces}")
	code = frappe.db.get_value("Dental Procedure", procedure.procedure, "procedure_code")
	if code:
		bits.append(f"[{code}]")
	return " · ".join(bits)


def _split_insurance(si, procedure):
	"""Raise an Insurance Claim for the payer share of this invoice."""
	policy = frappe.get_all(
		"Patient Insurance Policy",
		filters={"parent": procedure.patient, "parenttype": "Patient",
		         "coverage_order": "Primary"},
		fields=["insurance_plan", "payer", "policy_number"], limit=1)
	if not policy:
		return
	policy = policy[0]
	claim = frappe.get_doc({
		"doctype": "Insurance Claim",
		"patient": procedure.patient,
		"payer": policy.payer,
		"insurance_plan": policy.insurance_plan,
		"policy_number": policy.policy_number,
		"clinic": procedure.clinic,
		"practitioner": procedure.practitioner,
		"sales_invoice": si.name,
		"claim_date": nowdate(),
	})
	claim.append("lines", {
		"procedure": procedure.procedure,
		"procedure_code": frappe.db.get_value(
			"Dental Procedure", procedure.procedure, "procedure_code"),
		"tooth": procedure.tooth,
		"surfaces": procedure.surfaces,
		"service_date": getdate(procedure.procedure_date),
		"billed_amount": flt(procedure.rate),
		"clinical_procedure": procedure.name,
	})
	claim.insert(ignore_permissions=True)
	frappe.db.set_value("Clinical Procedure", procedure.name, "insurance_claim", claim.name)


def invoice_for_appointment(appointment):
	si = _base_invoice(appointment.patient, appointment.clinic, appointment.name)
	si.neo_dentiq_practitioner = appointment.practitioner
	for row in appointment.procedures:
		item = frappe.db.get_value("Dental Procedure", row.procedure, "item")
		if not item:
			continue
		si.append("items", {"item_code": item, "qty": 1, "rate": flt(row.fee)})
	if not si.items:
		frappe.throw(_("No billable procedures on this appointment."))
	si.insert(ignore_permissions=True)
	return si.name


def charge_no_show_fee(appointment, fee_item):
	si = _base_invoice(appointment.patient, appointment.clinic, appointment.name)
	si.append("items", {"item_code": fee_item, "qty": 1})
	si.remarks = f"Missed appointment fee — {appointment.name} on {appointment.appointment_date}"
	si.insert(ignore_permissions=True)
	si.submit()
	return si.name


def dispense_medications(prescription):
	s = _settings()
	warehouse = s.default_consumption_warehouse
	if not warehouse:
		return None
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Issue"
	se.company = s.default_company
	se.remarks = f"Dispensed against {prescription.name}"
	added = 0
	for row in prescription.items:
		item = frappe.db.get_value("Medication Master", row.medication, "item")
		if not item or not frappe.db.get_value("Item", item, "is_stock_item"):
			continue
		se.append("items", {"item_code": item, "qty": flt(row.quantity) or 1,
		                    "s_warehouse": warehouse})
		added += 1
	if not added:
		return None
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name


def payer_payment_entry(claim):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
	if not claim.sales_invoice:
		frappe.throw(_("Link the patient Sales Invoice before posting payer payment."))
	pe = get_payment_entry("Sales Invoice", claim.sales_invoice)
	pe.paid_amount = flt(claim.total_paid)
	pe.received_amount = flt(claim.total_paid)
	pe.reference_no = claim.payer_claim_number or claim.name
	pe.reference_date = nowdate()
	for ref in pe.references:
		ref.allocated_amount = flt(claim.total_paid)
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe.name


def collect_installment(plan_name, installment_idx, mode_of_payment=None):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
	plan = frappe.get_doc("Patient Payment Plan", plan_name)
	row = plan.installments[int(installment_idx) - 1]
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = _customer(plan.patient)
	pe.paid_amount = flt(row.amount)
	pe.received_amount = flt(row.amount)
	pe.company = _settings().default_company
	pe.mode_of_payment = mode_of_payment or "Cash"
	pe.reference_no = plan.name
	pe.reference_date = nowdate()
	pe.insert(ignore_permissions=True)
	row.db_set("status", "Paid")
	row.db_set("paid_on", nowdate())
	row.db_set("payment_entry", pe.name)
	plan.reload()
	plan.track()
	plan.db_update()
	return pe.name
