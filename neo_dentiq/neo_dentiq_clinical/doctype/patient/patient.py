# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, date_diff, getdate, nowdate, today


class Patient(Document):
	def validate(self):
		self.set_full_name()
		self.set_age()
		self.validate_guardian()
		self.set_alert_summary()

	def before_insert(self):
		if not self.clinic:
			self.clinic = frappe.db.get_single_value("Neo Dentiq Settings", "default_clinic")

	def after_insert(self):
		self.create_customer()
		if frappe.db.get_single_value("Neo Dentiq Settings", "auto_create_dental_chart"):
			self.create_dental_chart()
		self.schedule_first_recall()

	def on_update(self):
		self.sync_customer()

	# ------------------------------------------------------------ helpers
	def set_full_name(self):
		self.patient_name = " ".join(
			p for p in [self.first_name, self.middle_name, self.last_name] if p
		)

	def set_age(self):
		if not self.dob:
			return
		if getdate(self.dob) > getdate(today()):
			frappe.throw(_("Date of Birth cannot be in the future"))
		days = date_diff(today(), self.dob)
		years = days // 365
		months = (days % 365) // 30
		self.age = f"{years}y {months}m"
		self.is_minor = 1 if years < 18 else 0

	def validate_guardian(self):
		if self.is_minor and not self.guardian_name:
			frappe.msgprint(
				_("Patient is a minor. A guardian name is required before consent can be signed."),
				indicator="orange", alert=True,
			)

	def set_alert_summary(self):
		"""Build the red banner shown at the top of every clinical screen."""
		alerts = []
		for row in self.allergies or []:
			if row.severity in ("Severe", "Anaphylaxis"):
				alerts.append(f"ALLERGY: {row.allergy} ({row.severity})")
			else:
				alerts.append(f"Allergy: {row.allergy}")
		for row in self.medical_alerts or []:
			if row.status == "Resolved":
				continue
			meta = frappe.db.get_value(
				"Medical Alert Master", row.medical_alert,
				["severity", "requires_antibiotic_prophylaxis", "bleeding_risk",
				 "avoid_vasoconstrictor", "requires_medical_clearance"], as_dict=True,
			) or {}
			tags = []
			if meta.get("requires_antibiotic_prophylaxis"):
				tags.append("AB prophylaxis")
			if meta.get("bleeding_risk"):
				tags.append("bleeding risk")
			if meta.get("avoid_vasoconstrictor"):
				tags.append("no vasoconstrictor")
			if meta.get("requires_medical_clearance"):
				tags.append("medical clearance")
			label = row.medical_alert + (f" [{', '.join(tags)}]" if tags else "")
			alerts.append(label)
		if self.is_pregnant:
			alerts.append(f"PREGNANT (week {self.pregnancy_week or '?'})")
		if self.history_last_reviewed:
			stale = frappe.db.get_single_value(
				"Neo Dentiq Settings", "require_medical_history_review_days") or 180
			if date_diff(today(), self.history_last_reviewed) > stale:
				alerts.append("Medical history overdue for review")
		self.flags.alert_list = alerts

	# ------------------------------------------------------------ ERPNext
	def create_customer(self):
		if self.customer:
			return
		settings = frappe.get_single("Neo Dentiq Settings")
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": self.patient_name,
			"customer_type": "Individual",
			"customer_group": _get_or_create_customer_group(),
			"territory": frappe.db.get_single_value("Selling Settings", "territory")
			or "All Territories",
			"default_price_list": settings.default_price_list,
			"mobile_no": self.mobile,
			"email_id": self.email,
		}).insert(ignore_permissions=True)
		self.db_set("customer", customer.name, update_modified=False)

	def sync_customer(self):
		if not self.customer:
			return
		changes = {}
		if frappe.db.get_value("Customer", self.customer, "customer_name") != self.patient_name:
			changes["customer_name"] = self.patient_name
		if changes:
			frappe.db.set_value("Customer", self.customer, changes)

	def create_dental_chart(self):
		if frappe.db.exists("Dental Chart", {"patient": self.name}):
			return
		chart = frappe.new_doc("Dental Chart")
		chart.patient = self.name
		chart.dentition = "Primary" if _years(self.dob) < 6 else "Permanent"
		chart.numbering_system = (
			frappe.db.get_single_value("Neo Dentiq Settings", "tooth_numbering_system") or "FDI"
		)
		chart.build_default_teeth()
		chart.insert(ignore_permissions=True)

	def schedule_first_recall(self):
		recall_type = self.recall_type or frappe.db.get_single_value(
			"Neo Dentiq Settings", "default_recall_type")
		if not recall_type:
			return
		months = frappe.db.get_value("Recall Type", recall_type, "interval_months") or 6
		due = add_months(nowdate(), months)
		frappe.get_doc({
			"doctype": "Recall Schedule",
			"patient": self.name,
			"recall_type": recall_type,
			"due_date": due,
			"interval_months": months,
			"practitioner": self.primary_practitioner,
			"clinic": self.clinic,
		}).insert(ignore_permissions=True)
		self.db_set("next_recall_date", due, update_modified=False)

	# ------------------------------------------------------------ api
	@frappe.whitelist()
	def get_alerts(self):
		self.set_alert_summary()
		return self.flags.alert_list

	@frappe.whitelist()
	def refresh_financials(self):
		from neo_dentiq.utils.metrics import recompute_patient_metrics
		recompute_patient_metrics(self.name)
		self.reload()
		return {"lifetime_value": self.lifetime_value, "no_show_score": self.no_show_score}


def _years(dob):
	if not dob:
		return 99
	return date_diff(today(), dob) // 365


def _get_or_create_customer_group():
	name = "Dental Patients"
	if not frappe.db.exists("Customer Group", name):
		frappe.get_doc({
			"doctype": "Customer Group",
			"customer_group_name": name,
			"parent_customer_group": "All Customer Groups",
			"is_group": 0,
		}).insert(ignore_permissions=True)
	return name
