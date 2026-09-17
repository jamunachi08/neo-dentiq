# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (add_to_date, cint, flt, get_datetime, get_time, getdate,
                          now_datetime, nowdate, time_diff_in_seconds)

from neo_dentiq.utils.no_show import score_appointment
from neo_dentiq.utils.scheduling import check_conflicts, validate_practitioner_licence


class DentalAppointment(Document):
	def validate(self):
		self.set_defaults()
		self.set_duration()
		self.set_end_time()
		validate_practitioner_licence(self.practitioner, self.appointment_date)
		self.validate_past()
		check_conflicts(self)
		self.score_risk()
		self.set_colour()

	def before_insert(self):
		self.is_new_patient = 0 if frappe.db.exists(
			"Dental Appointment",
			{"patient": self.patient, "status": "Completed", "name": ("!=", self.name)},
		) else 1

	def after_insert(self):
		self.send_intake_form()

	def on_update(self):
		self.handle_status_change()

	# ------------------------------------------------------------
	def set_defaults(self):
		if not self.clinic:
			self.clinic = frappe.db.get_value("Patient", self.patient, "clinic") \
				or frappe.db.get_single_value("Neo Dentiq Settings", "default_clinic")
		if not self.operatory:
			self.operatory = frappe.db.get_value(
				"Dental Practitioner", self.practitioner, "default_operatory")
		kit = None
		for row in self.procedures or []:
			kit = frappe.db.get_value("Dental Procedure", row.procedure, "instrument_kit")
			if kit:
				break
		self.instrument_kit = kit

	def set_duration(self):
		if self.procedures:
			total = sum(cint(r.duration) for r in self.procedures)
			if total:
				self.duration = total
				return
		if not self.duration:
			self.duration = cint(frappe.db.get_value(
				"Appointment Type", self.appointment_type, "default_duration")) or 30

	def set_end_time(self):
		start = get_datetime(f"{self.appointment_date} {self.appointment_time}")
		self.end_time = add_to_date(start, minutes=cint(self.duration)).strftime("%H:%M:%S")

	def validate_past(self):
		if self.is_new() and getdate(self.appointment_date) < getdate(nowdate()):
			frappe.throw(_("Cannot book an appointment in the past."))

	def score_risk(self):
		if self.status in ("Completed", "Cancelled", "No Show"):
			return
		result = score_appointment(self)
		self.no_show_risk = result["score"]
		self.risk_band = result["band"]
		self.risk_factors = "; ".join(result["factors"])

	def set_colour(self):
		self.color = frappe.db.get_value(
			"Appointment Type", self.appointment_type, "colour") or "#2563eb"

	# ------------------------------------------------------------ status
	def handle_status_change(self):
		before = self.get_doc_before_save()
		if not before or before.status == self.status:
			return
		handler = {
			"Arrived": self._on_arrived,
			"In Operatory": self._on_seated,
			"Completed": self._on_completed,
			"Cancelled": self._on_cancelled,
			"No Show": self._on_no_show,
		}.get(self.status)
		if handler:
			handler()

	def _on_arrived(self):
		self.db_set("arrived_at", now_datetime(), update_modified=False)

	def _on_seated(self):
		now = now_datetime()
		self.db_set("seated_at", now, update_modified=False)
		if self.arrived_at:
			wait = time_diff_in_seconds(now, self.arrived_at) / 60.0
			self.db_set("wait_minutes", int(wait), update_modified=False)

	def _on_completed(self):
		self.db_set("completed_at", now_datetime(), update_modified=False)
		frappe.db.set_value("Patient", self.patient, "last_visit_date", self.appointment_date)
		production = flt(frappe.db.get_value(
			"Sales Invoice", {"neo_dentiq_appointment": self.name, "docstatus": 1},
			"sum(grand_total)")) or sum(flt(r.fee) for r in self.procedures or [])
		self.db_set("production_value", production, update_modified=False)

	def _on_cancelled(self):
		self._release_slot()

	def _on_no_show(self):
		from neo_dentiq.utils.no_show import record_no_show
		record_no_show(self)
		self._release_slot()

	def _release_slot(self):
		if not frappe.db.get_single_value("Neo Dentiq Settings", "auto_fill_from_waitlist"):
			return
		reason_ok = True
		if self.cancellation_reason:
			reason_ok = bool(frappe.db.get_value(
				"Cancellation Reason", self.cancellation_reason, "release_slot_to_waitlist"))
		if reason_ok:
			frappe.enqueue(
				"neo_dentiq.utils.waitlist.offer_slot", queue="short",
				appointment=self.name,
			)

	# ------------------------------------------------------------ actions
	def send_intake_form(self):
		tpl = frappe.db.get_value(
			"Appointment Type", self.appointment_type,
			["requires_intake_form", "intake_form_template"], as_dict=True) or {}
		if not tpl.get("requires_intake_form"):
			return
		resp = frappe.get_doc({
			"doctype": "Patient Intake Response",
			"patient": self.patient,
			"template": tpl.get("intake_form_template"),
			"appointment": self.name,
			"status": "Pending",
		}).insert(ignore_permissions=True)
		self.db_set("intake_response", resp.name, update_modified=False)
		self.db_set("intake_status", "Sent", update_modified=False)

	@frappe.whitelist()
	def create_clinical_note(self):
		note = frappe.get_doc({
			"doctype": "Clinical Note",
			"patient": self.patient,
			"appointment": self.name,
			"practitioner": self.practitioner,
			"clinic": self.clinic,
			"operatory": self.operatory,
			"chief_complaint": self.reason or "Routine visit",
		}).insert()
		self.db_set("clinical_note", note.name)
		return note.name

	@frappe.whitelist()
	def create_invoice(self):
		from neo_dentiq.utils.billing import invoice_for_appointment
		si = invoice_for_appointment(self)
		self.db_set("sales_invoice", si)
		return si

	@frappe.whitelist()
	def send_reminder(self):
		from neo_dentiq.utils.messaging import send_appointment_reminder
		return send_appointment_reminder(self)
