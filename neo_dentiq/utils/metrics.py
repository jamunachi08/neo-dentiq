"""Practice KPIs: production, utilisation, acceptance, recall effectiveness."""
import frappe
from frappe.utils import add_days, add_months,cint, date_diff, flt, getdate, nowdate


def recompute_patient_metrics(patient=None):
	filters = {"name": patient} if patient else {"status": "Active"}
	for row in frappe.get_all("Patient", filters=filters,
	                          fields=["name", "customer", "last_visit_date"]):
		ltv = 0
		if row.customer:
			ltv = flt(frappe.db.sql("""
				select sum(grand_total) from `tabSales Invoice`
				where customer = %s and docstatus = 1
			""", row.customer)[0][0])
		gap = date_diff(nowdate(), row.last_visit_date) if row.last_visit_date else None
		dose = flt(frappe.db.sql("""
			select sum(effective_dose_msv) from `tabRadiograph Record` where patient = %s
		""", row.name)[0][0])
		frappe.db.set_value("Patient", row.name, {
			"lifetime_value": ltv,
			"inactive_since_days": gap,
			"cumulative_radiation_msv": dose,
		}, update_modified=False)
	frappe.db.commit()


@frappe.whitelist()
def practice_kpis(clinic=None, from_date=None, to_date=None):
	to_date = to_date or nowdate()
	from_date = from_date or add_months(to_date, -1)
	clinic_filter = " and clinic = %(clinic)s" if clinic else ""
	args = {"from_date": from_date, "to_date": to_date, "clinic": clinic}

	appts = frappe.db.sql(f"""
		select status, count(*) as c, sum(duration) as mins
		from `tabDental Appointment`
		where appointment_date between %(from_date)s and %(to_date)s {clinic_filter}
		group by status
	""", args, as_dict=True)
	by_status = {r.status: r.c for r in appts}
	total = sum(by_status.values()) or 1
	completed = by_status.get("Completed", 0)

	production = flt(frappe.db.sql("""
		select sum(grand_total) from `tabSales Invoice`
		where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s
	""", args)[0][0])
	collection = flt(frappe.db.sql("""
		select sum(paid_amount) from `tabPayment Entry`
		where docstatus = 1 and payment_type = 'Receive'
		  and posting_date between %(from_date)s and %(to_date)s
	""", args)[0][0])

	plans = frappe.db.sql("""
		select sum(total_fee) as planned, sum(accepted_fee) as accepted
		from `tabTreatment Plan`
		where docstatus = 1 and plan_date between %(from_date)s and %(to_date)s
	""", args, as_dict=True)[0]

	chair_minutes = flt(frappe.db.sql(f"""
		select sum(duration) from `tabDental Appointment`
		where status = 'Completed' and appointment_date between %(from_date)s
		  and %(to_date)s {clinic_filter}
	""", args)[0][0])

	recalls = frappe.db.sql("""
		select status, count(*) as c from `tabRecall Schedule`
		where due_date between %(from_date)s and %(to_date)s group by status
	""", args, as_dict=True)
	recall_map = {r.status: r.c for r in recalls}
	recall_total = sum(recall_map.values()) or 1

	return {
		"appointments": total,
		"completed": completed,
		"no_show_rate": round(by_status.get("No Show", 0) * 100.0 / total, 1),
		"cancellation_rate": round(by_status.get("Cancelled", 0) * 100.0 / total, 1),
		"production": production,
		"collection": collection,
		"collection_rate": round(collection * 100.0 / production, 1) if production else 0,
		"case_acceptance_rate": round(
			flt(plans.accepted) * 100.0 / flt(plans.planned), 1) if flt(plans.planned) else 0,
		"production_per_chair_hour": round(production / (chair_minutes / 60.0), 2)
		if chair_minutes else 0,
		"recall_effectiveness": round(
			(recall_map.get("Booked", 0) + recall_map.get("Completed", 0))
			* 100.0 / recall_total, 1),
		"active_patients": frappe.db.count("Patient", {"status": "Active"}),
		"new_patients": frappe.db.count("Patient", {
			"creation": ["between", (from_date, to_date)]}),
	}


@frappe.whitelist()
def operatory_utilisation(clinic=None, from_date=None, to_date=None):
	to_date = to_date or nowdate()
	from_date = from_date or add_days(to_date, -30)
	rows = frappe.db.sql("""
		select a.operatory, sum(a.duration) as booked_minutes,
		       count(*) as appointments,
		       sum(case when a.status = 'Completed' then a.duration else 0 end) as used_minutes
		from `tabDental Appointment` a
		where a.appointment_date between %s and %s
		  and a.status not in ('Cancelled','Rescheduled')
		group by a.operatory
	""", (from_date, to_date), as_dict=True)
	days = max(date_diff(to_date, from_date), 1)
	capacity = days * 8 * 60
	for r in rows:
		r["utilisation_percent"] = round(flt(r.used_minutes) * 100.0 / capacity, 1)
		cost = flt(frappe.db.get_value(
			"Dental Operatory", r.operatory, "hourly_operating_cost"))
		r["operating_cost"] = round(cost * flt(r.used_minutes) / 60.0, 2)
	return rows
