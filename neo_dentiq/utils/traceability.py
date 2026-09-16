"""Sterilisation and material traceability: tray -> cycle -> patient."""
import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate


def assert_trays_sterile(procedure):
	"""Hard gate: no unsterile, expired, failed or over-cycled tray reaches a patient."""
	if not procedure.trays_used:
		kit = frappe.db.get_value("Dental Procedure", procedure.procedure, "instrument_kit")
		if kit:
			frappe.throw(_(
				"Procedure {0} requires instrument kit {1}. Scan the tray barcode before "
				"submitting so the sterilisation chain stays unbroken."
			).format(procedure.procedure, kit))
		return

	for row in procedure.trays_used:
		tray = frappe.get_doc("Instrument Tray", row.instrument_tray)
		if tray.status == "Retired":
			frappe.throw(_("Tray {0} is retired ({1} cycles).")
			             .format(tray.name, tray.cycle_count))
		if tray.last_cycle_result != "Pass":
			frappe.throw(_(
				"Tray {0} has no passed sterilisation cycle on record (last result: {1})."
			).format(tray.name, tray.last_cycle_result or "none"))
		if tray.sterile_until and getdate(tray.sterile_until) < getdate(procedure.procedure_date):
			frappe.throw(_("Tray {0} sterility expired on {1}. Reprocess before use.")
			             .format(tray.name, tray.sterile_until))
		row.sterilization_cycle = tray.last_cycle
		row.cycle_result = tray.last_cycle_result


def mark_trays_used(procedure):
	for row in procedure.trays_used or []:
		frappe.db.set_value("Instrument Tray", row.instrument_tray, {
			"status": "Dirty / Awaiting Reprocessing",
			"last_used_on": now_datetime(),
			"last_used_patient": procedure.patient,
		}, update_modified=False)


def consume_consumables(procedure):
	"""Post a Material Issue Stock Entry so chairside usage hits real inventory."""
	settings = frappe.get_cached_doc("Neo Dentiq Settings")
	warehouse = (
		frappe.db.get_value("Dental Clinic", procedure.clinic, "default_warehouse")
		or settings.default_consumption_warehouse
	)
	if not warehouse:
		frappe.msgprint(_("No chairside warehouse configured; stock was not consumed."),
		                alert=True)
		return None

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Issue"
	se.purpose = "Material Issue"
	se.company = settings.default_company
	se.posting_date = getdate(procedure.procedure_date)
	se.set_posting_time = 1
	se.neo_dentiq_clinical_procedure = procedure.name
	se.remarks = f"Chairside consumption for {procedure.name} ({procedure.patient_name})"

	added = 0
	for row in procedure.consumables:
		if not frappe.db.get_value("Item", row.item_code, "is_stock_item"):
			continue
		se.append("items", {
			"item_code": row.item_code,
			"qty": flt(row.qty),
			"uom": row.uom,
			"s_warehouse": row.warehouse or warehouse,
			"batch_no": row.batch_no,
			"serial_no": row.serial_no if frappe.db.exists("Serial No", row.serial_no) else None,
			"cost_center": frappe.db.get_value("Dental Clinic", procedure.clinic, "cost_center"),
		})
		added += 1
	if not added:
		return None
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name


@frappe.whitelist()
def trace_patient(patient):
	"""Full reverse-traceability dossier for a patient — audit and recall ready."""
	procedures = frappe.get_all(
		"Clinical Procedure",
		filters={"patient": patient, "docstatus": 1},
		fields=["name", "procedure", "procedure_date", "practitioner", "tooth"],
		order_by="procedure_date desc",
	)
	for proc in procedures:
		proc["trays"] = frappe.get_all(
			"Procedure Tray Used", filters={"parent": proc.name},
			fields=["instrument_tray", "sterilization_cycle", "cycle_result"])
		proc["materials"] = frappe.get_all(
			"Procedure Consumable Used", filters={"parent": proc.name},
			fields=["item_code", "item_name", "batch_no", "serial_no", "expiry_date"])
	return procedures


@frappe.whitelist()
def trace_batch(batch_no):
	"""Which patients received a given lot — for a manufacturer recall."""
	return frappe.db.sql("""
		select cp.name as procedure, cp.patient, cp.patient_name, cp.procedure_date,
		       pcu.item_code, pcu.batch_no, pcu.serial_no
		from `tabProcedure Consumable Used` pcu
		join `tabClinical Procedure` cp on cp.name = pcu.parent
		where pcu.batch_no = %s and cp.docstatus = 1
		order by cp.procedure_date desc
	""", batch_no, as_dict=True)


@frappe.whitelist()
def trace_cycle(cycle):
	"""Which patients were treated with trays from a given sterilisation load."""
	return frappe.db.sql("""
		select cp.name as procedure, cp.patient, cp.patient_name, cp.procedure_date,
		       ptu.instrument_tray
		from `tabProcedure Tray Used` ptu
		join `tabClinical Procedure` cp on cp.name = ptu.parent
		where ptu.sterilization_cycle = %s and cp.docstatus = 1
	""", cycle, as_dict=True)
