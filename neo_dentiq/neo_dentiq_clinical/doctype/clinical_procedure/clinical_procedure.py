# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, flt, getdate, now_datetime, nowdate

from neo_dentiq.utils.traceability import (
	assert_trays_sterile, mark_trays_used, consume_consumables,
)


class ClinicalProcedure(Document):
	def validate(self):
		self.set_defaults()
		self.validate_consent()
		self.validate_tooth_scope()
		self.validate_expiry()
		self.set_warranty()

	def before_submit(self):
		settings = frappe.get_single("Neo Dentiq Settings")
		if settings.enforce_sterilization_traceability:
			assert_trays_sterile(self)

	def on_submit(self):
		settings = frappe.get_single("Neo Dentiq Settings")
		mark_trays_used(self)
		if settings.auto_consume_stock_on_procedure and self.consumables:
			self.stock_entry = consume_consumables(self)
			self.db_set("stock_entry", self.stock_entry)
		self.update_dental_chart()
		self.update_treatment_plan()
		self.create_implant_record()
		if self.is_billable and settings.auto_create_sales_invoice:
			self.create_sales_invoice()
		self.bump_patient_stats()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Stock Entry", "Sales Invoice")

	# ------------------------------------------------------------
	def set_defaults(self):
		if not self.clinic:
			self.clinic = frappe.db.get_value("Patient", self.patient, "clinic")
		if not self.rate:
			self.rate = flt(frappe.db.get_value("Dental Procedure", self.procedure, "standard_rate"))
		if not self.consumables:
			self.pull_default_consumables()

	def pull_default_consumables(self):
		defaults = frappe.get_all(
			"Dental Procedure Consumable",
			filters={"parent": self.procedure, "parenttype": "Dental Procedure"},
			fields=["item_code", "qty", "uom", "is_billable", "requires_lot_capture"],
		)
		for d in defaults:
			self.append("consumables", d)

	def validate_consent(self):
		proc = frappe.db.get_value(
			"Dental Procedure", self.procedure, ["requires_consent", "tooth_scope"], as_dict=True
		) or {}
		if not proc.get("requires_consent"):
			self.consent_verified = 1
			return
		if self.consent_record:
			status, valid_till = frappe.db.get_value(
				"Consent Record", self.consent_record, ["status", "valid_till"])
			if status == "Signed" and (not valid_till or getdate(valid_till) >= getdate(nowdate())):
				self.consent_verified = 1
				return
		self.consent_verified = 0
		if frappe.db.get_single_value("Neo Dentiq Settings", "require_consent_before_procedure"):
			frappe.throw(_(
				"{0} requires a signed, in-date consent form. Capture consent before recording it."
			).format(self.procedure))

	def validate_tooth_scope(self):
		scope = frappe.db.get_value("Dental Procedure", self.procedure, "tooth_scope")
		if scope in ("Per Tooth", "Per Surface", "Per Root") and not self.tooth:
			frappe.throw(_("{0} is charted per tooth — select the tooth.").format(self.procedure))
		if scope == "Per Surface" and not self.surfaces:
			frappe.throw(_("{0} requires the surfaces treated (e.g. MOD).").format(self.procedure))
		if scope == "Per Quadrant" and not self.quadrant:
			frappe.throw(_("{0} requires a quadrant.").format(self.procedure))

	def validate_expiry(self):
		if not frappe.db.get_single_value("Neo Dentiq Settings", "expired_stock_block"):
			return
		for row in self.consumables:
			if not row.batch_no:
				continue
			expiry = frappe.db.get_value("Batch", row.batch_no, "expiry_date")
			row.expiry_date = expiry
			if expiry and getdate(expiry) < getdate(self.procedure_date):
				frappe.throw(_("Row {0}: batch {1} of {2} expired on {3}.").format(
					row.idx, row.batch_no, row.item_code, expiry))

	def set_warranty(self):
		months = cint(frappe.db.get_value("Dental Procedure", self.procedure, "warranty_months"))
		if months:
			self.warranty_expiry = add_months(getdate(self.procedure_date), months)

	# ------------------------------------------------------------ downstream
	def update_dental_chart(self):
		if not self.tooth:
			return
		chart_name = frappe.db.get_value("Dental Chart", {"patient": self.patient})
		if not chart_name:
			return
		mapping = _chart_effect(self.procedure)
		if not mapping:
			return
		chart = frappe.get_doc("Dental Chart", chart_name)
		row = next((r for r in chart.teeth if r.tooth == self.tooth), None)
		if not row:
			row = chart.append("teeth", {"tooth": self.tooth})
		if mapping.get("status"):
			row.status = mapping["status"]
		if mapping.get("condition"):
			row.condition = mapping["condition"]
		if self.surfaces:
			row.surfaces = self.surfaces
		row.source_procedure = self.name
		row.last_updated_on = nowdate()
		chart.save(ignore_permissions=True)

	def update_treatment_plan(self):
		if not (self.treatment_plan and self.treatment_plan_item):
			return
		frappe.db.set_value("Treatment Plan Item", self.treatment_plan_item, {
			"status": "Completed", "completed_procedure": self.name,
		})
		tp = frappe.get_doc("Treatment Plan", self.treatment_plan)
		tp.compute_totals()
		tp.set_status()
		tp.db_update()

	def create_implant_record(self):
		implant_rows = [
			r for r in self.consumables
			if frappe.db.get_value("Item", r.item_code, "item_group") == "Dental Implants"
		]
		if not implant_rows:
			return
		row = implant_rows[0]
		if frappe.db.get_single_value("Neo Dentiq Settings", "enforce_udi_capture") and not (
			row.serial_no or row.batch_no
		):
			frappe.throw(_("Capture the UDI / lot number for implant {0}.").format(row.item_code))
		rec = frappe.get_doc({
			"doctype": "Implant Record",
			"patient": self.patient,
			"tooth": self.tooth,
			"placement_date": getdate(self.procedure_date),
			"practitioner": self.practitioner,
			"clinical_procedure": self.name,
			"item_code": row.item_code,
			"serial_no": row.serial_no if frappe.db.exists("Serial No", row.serial_no) else None,
			"udi_pi": row.serial_no,
			"batch_no": row.batch_no,
			"expiry_date": row.expiry_date,
			"warranty_expiry": self.warranty_expiry,
		}).insert(ignore_permissions=True)
		self.db_set("implant_record", rec.name)

	def create_sales_invoice(self):
		from neo_dentiq.utils.billing import invoice_for_procedure
		si = invoice_for_procedure(self)
		if si:
			self.db_set("sales_invoice", si)

	def bump_patient_stats(self):
		frappe.db.set_value("Patient", self.patient, "last_visit_date",
		                    getdate(self.procedure_date))


def _chart_effect(procedure):
	"""Map a completed procedure onto the odontogram."""
	cat = (frappe.db.get_value("Dental Procedure", procedure, "category") or "").lower()
	name = (procedure or "").lower()
	if "extract" in name or "extraction" in cat:
		return {"status": "Extracted", "condition": "Sound"}
	if "implant" in name:
		return {"status": "Implant"}
	if "root canal" in name or "endodont" in cat:
		return {"condition": "Root Canal Treated"}
	if "crown" in name:
		return {"condition": "Crowned"}
	if "veneer" in name:
		return {"condition": "Veneered"}
	if "filling" in name or "restor" in cat or "composite" in name or "amalgam" in name:
		return {"condition": "Restored"}
	return None
