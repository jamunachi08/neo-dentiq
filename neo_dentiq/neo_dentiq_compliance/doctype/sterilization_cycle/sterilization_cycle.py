# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, now_datetime


class SterilizationCycle(Document):
	def validate(self):
		self.evaluate_result()
		self.validate_parameters()

	def on_submit(self):
		self.update_trays()
		if self.cycle_result == "Fail":
			self.trigger_recall()

	# ------------------------------------------------------------
	def evaluate_result(self):
		fail = (
			self.chemical_indicator_result == "Fail"
			or self.bowie_dick_result == "Fail"
			or self.vacuum_leak_test == "Fail"
			or (self.biological_indicator_used
			    and self.biological_indicator_result == "Fail")
		)
		pending = self.biological_indicator_used and \
			self.biological_indicator_result == "Pending"
		self.cycle_result = "Fail" if fail else ("Quarantined" if pending else "Pass")

	def validate_parameters(self):
		"""Reject cycles that never reached a validated sterilising condition."""
		minimums = {
			"Steam 134C": (134, 3), "Steam 134C Vacuum": (134, 3),
			"Steam 121C": (121, 15), "Chemical Vapour": (132, 20),
			"Dry Heat": (160, 60), "Ethylene Oxide": (55, 180),
		}
		temp_min, time_min = minimums.get(self.cycle_type, (0, 0))
		if temp_min and (self.temperature_c or 0) < temp_min - 1:
			frappe.msgprint(
				_("Temperature {0}C is below the validated minimum of {1}C for {2}.")
				.format(self.temperature_c, temp_min, self.cycle_type),
				indicator="red", alert=True)
			self.cycle_result = "Fail"
		if time_min and (self.hold_time_minutes or 0) < time_min:
			frappe.msgprint(
				_("Hold time {0} min is below the validated minimum of {1} min.")
				.format(self.hold_time_minutes, time_min),
				indicator="red", alert=True)
			self.cycle_result = "Fail"

	def update_trays(self):
		sterile_until = add_days(getdate(self.cycle_datetime),
		                         cint(self.sterile_shelf_life_days) or 30)
		for row in self.trays:
			result = "Fail" if self.cycle_result == "Fail" else row.result
			tray = frappe.get_doc("Instrument Tray", row.instrument_tray)
			tray.last_cycle = self.name
			tray.last_cycle_result = "Pass" if result == "Pass" else "Fail"
			tray.last_cycle_date = self.cycle_datetime
			tray.cycle_count = cint(tray.cycle_count) + 1
			if result == "Pass" and self.cycle_result == "Pass":
				tray.status = "Available (Sterile)"
				tray.sterile_until = sterile_until
				tray.is_expired = 0
			else:
				tray.status = "Quarantined"
				tray.sterile_until = None
			if tray.max_reuse_count and tray.cycle_count >= tray.max_reuse_count:
				tray.status = "Retired"
			tray.save(ignore_permissions=True)

	def trigger_recall(self):
		"""A failed cycle means every patient treated with those trays must be traced."""
		trays = [r.instrument_tray for r in self.trays]
		if not trays:
			return
		rows = frappe.db.sql("""
			select distinct cp.name, cp.patient, cp.patient_name, cp.procedure_date
			from `tabClinical Procedure` cp
			join `tabProcedure Tray Used` ptu on ptu.parent = cp.name
			where ptu.instrument_tray in %(trays)s
			  and cp.procedure_date >= %(since)s and cp.docstatus = 1
		""", {"trays": trays, "since": self.cycle_datetime}, as_dict=True)
		if not rows:
			return
		affected = ", ".join(f"{r.patient_name} ({r.patient})" for r in rows)
		self.db_set("recall_triggered", 1)
		self.db_set("affected_patients", affected)
		incident = frappe.get_doc({
			"doctype": "Clinical Incident",
			"incident_datetime": now_datetime(),
			"clinic": self.clinic,
			"incident_type": "Sterilization Failure",
			"severity": "Major",
			"reported_by": frappe.session.user,
			"description": (
				f"Sterilization cycle {self.name} on {self.sterilizer} failed. "
				f"{len(rows)} patient procedure(s) used trays from this load: {affected}"
			),
			"immediate_action": "Trays quarantined. Patients flagged for clinical review and "
			                    "post-exposure risk assessment.",
			"reportable_to_authority": 1,
		}).insert(ignore_permissions=True)
		frappe.msgprint(
			_("Failed cycle: {0} patient procedure(s) traced. Incident {1} raised.")
			.format(len(rows), incident.name), indicator="red")
