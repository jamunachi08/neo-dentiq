"""Practice-intelligence endpoints powering the dashboards."""
import frappe
from frappe.utils import add_days, add_months, flt, nowdate

from neo_dentiq.utils.metrics import operatory_utilisation, practice_kpis


@frappe.whitelist()
def kpis(clinic=None, from_date=None, to_date=None):
	return practice_kpis(clinic, from_date, to_date)


@frappe.whitelist()
def chair_utilisation(clinic=None, from_date=None, to_date=None):
	return operatory_utilisation(clinic, from_date, to_date)


@frappe.whitelist()
def production_by_practitioner(from_date=None, to_date=None):
	to_date = to_date or nowdate()
	from_date = from_date or add_months(to_date, -1)
	return frappe.db.sql("""
		select cp.practitioner, count(*) as procedures, sum(cp.rate) as production,
		       sum(cp.chair_time_minutes) as chair_minutes
		from `tabClinical Procedure` cp
		where cp.docstatus = 1 and cp.procedure_date between %s and %s
		group by cp.practitioner order by production desc
	""", (from_date, to_date), as_dict=True)


@frappe.whitelist()
def case_acceptance(from_date=None, to_date=None):
	to_date = to_date or nowdate()
	from_date = from_date or add_months(to_date, -3)
	return frappe.db.sql("""
		select practitioner, count(*) as plans, sum(total_fee) as presented,
		       sum(accepted_fee) as accepted,
		       round(sum(accepted_fee) * 100 / nullif(sum(total_fee), 0), 1) as rate
		from `tabTreatment Plan`
		where docstatus = 1 and plan_date between %s and %s
		group by practitioner order by rate desc
	""", (from_date, to_date), as_dict=True)


@frappe.whitelist()
def revenue_trend(months=12):
	return frappe.db.sql("""
		select date_format(posting_date, '%%Y-%%m') as month,
		       sum(grand_total) as production,
		       sum(grand_total - outstanding_amount) as collected
		from `tabSales Invoice`
		where docstatus = 1 and posting_date >= %s
		group by month order by month
	""", add_months(nowdate(), -int(months)), as_dict=True)


@frappe.whitelist()
def insurance_aging():
	return frappe.db.sql("""
		select payer,
			sum(case when aging_days <= 30 then outstanding else 0 end) as d0_30,
			sum(case when aging_days between 31 and 60 then outstanding else 0 end) as d31_60,
			sum(case when aging_days between 61 and 90 then outstanding else 0 end) as d61_90,
			sum(case when aging_days > 90 then outstanding else 0 end) as d90_plus,
			sum(outstanding) as total
		from `tabInsurance Claim`
		where docstatus = 1 and outstanding > 0
		group by payer order by total desc
	""", as_dict=True)


@frappe.whitelist()
def no_show_analysis(months=6):
	return frappe.db.sql("""
		select risk_band,
		       count(*) as total,
		       sum(case when status = 'No Show' then 1 else 0 end) as no_shows,
		       round(sum(case when status = 'No Show' then 1 else 0 end) * 100.0
		             / count(*), 1) as actual_rate
		from `tabDental Appointment`
		where appointment_date >= %s and status in ('Completed','No Show')
		  and risk_band is not null
		group by risk_band
	""", add_months(nowdate(), -int(months)), as_dict=True)


@frappe.whitelist()
def recall_effectiveness(months=6):
	return frappe.db.sql("""
		select recall_type, count(*) as due,
		       sum(case when status in ('Booked','Completed') then 1 else 0 end) as converted,
		       round(sum(case when status in ('Booked','Completed') then 1 else 0 end)
		             * 100.0 / count(*), 1) as rate
		from `tabRecall Schedule`
		where due_date >= %s group by recall_type
	""", add_months(nowdate(), -int(months)), as_dict=True)


@frappe.whitelist()
def lab_performance(months=6):
	return frappe.db.sql("""
		select lab, count(*) as cases,
		       sum(is_late) as late_cases,
		       sum(remake_count) as remakes,
		       round(avg(datediff(coalesce(received_date, curdate()), sent_date)), 1)
		         as avg_turnaround,
		       sum(lab_cost) as spend
		from `tabLab Case`
		where creation >= %s group by lab order by cases desc
	""", add_months(nowdate(), -int(months)), as_dict=True)


@frappe.whitelist()
def sterilization_compliance(months=3):
	return frappe.db.sql("""
		select sterilizer, count(*) as cycles,
		       sum(case when cycle_result = 'Pass' then 1 else 0 end) as passed,
		       sum(case when cycle_result = 'Fail' then 1 else 0 end) as failed,
		       sum(biological_indicator_used) as bi_tests
		from `tabSterilization Cycle`
		where docstatus = 1 and cycle_datetime >= %s group by sterilizer
	""", add_months(nowdate(), -int(months)), as_dict=True)


@frappe.whitelist()
def patient_acquisition(months=12):
	return frappe.db.sql("""
		select coalesce(referral_source, 'Unknown') as source, count(*) as patients,
		       sum(lifetime_value) as lifetime_value
		from `tabPatient` where creation >= %s
		group by source order by patients desc
	""", add_months(nowdate(), -int(months)), as_dict=True)
