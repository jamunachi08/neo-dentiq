from . import __version__ as app_version

app_name = "neo_dentiq"
app_title = "Neo Dentiq"
app_publisher = "Neo Dentiq"
app_description = "Dental practice management, clinical charting, sterilisation traceability and dental revenue cycle, built natively on Frappe/ERPNext."
app_email = "hello@neodentiq.app"
app_license = "MIT"
required_apps = ["frappe/erpnext"]

# ---------------------------------------------------------------- assets
app_include_css = "/assets/neo_dentiq/css/theme.css"
app_include_js = "/assets/neo_dentiq/js/neo_dentiq.bundle.js"

web_include_css = ["/assets/neo_dentiq/css/theme.css", "/assets/neo_dentiq/css/portal.css"]
web_include_js = "/assets/neo_dentiq/js/theme.js"

doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
}

# ---------------------------------------------------------------- portal
website_route_rules = [
	{"from_route": "/book", "to_route": "book"},
	{"from_route": "/my-dental", "to_route": "portal/dashboard"},
]

portal_menu_items = [
	{"title": "My Appointments", "route": "/my-dental",
	 "reference_doctype": "Dental Appointment", "role": "Patient Portal User"},
	{"title": "My Treatment Plans", "route": "/treatment-plans",
	 "reference_doctype": "Treatment Plan", "role": "Patient Portal User"},
]

# ---------------------------------------------------------------- boot
boot_session = "neo_dentiq.boot.boot_session"
update_website_context = "neo_dentiq.boot.website_context"

# ---------------------------------------------------------------- install
after_install = "neo_dentiq.install.after_install"
after_migrate = "neo_dentiq.install.after_migrate"

# ---------------------------------------------------------------- fixtures
fixtures = [
	{"dt": "Custom Field", "filters": [["name", "like", "%neo_dentiq%"]]},
	{"dt": "Workflow", "filters": [["name", "in", [
		"Neo Dentiq Treatment Plan Approval", "Neo Dentiq Lab Case Flow",
		"Neo Dentiq Insurance Claim Flow"]]]},
	{"dt": "Workflow State", "filters": [["name", "like", "Neo Dentiq%"]]},
	{"dt": "Role", "filters": [["name", "in", [
		"Neo Dentiq Manager", "Dentist", "Dental Hygienist", "Front Desk",
		"Insurance Coordinator", "Sterilization Officer", "Patient Portal User"]]]},
]

# ---------------------------------------------------------------- events
doc_events = {
	"Sales Invoice": {
		"on_submit": [
			"neo_dentiq.integrations.zatca.attach_to_invoice",
			"neo_dentiq.events.invoice.on_submit",
		],
	},
	"Payment Entry": {
		"on_submit": "neo_dentiq.events.payment.on_submit",
	},
	"Stock Ledger Entry": {
		"on_submit": "neo_dentiq.events.stock.check_reorder",
	},
}

# ---------------------------------------------------------------- scheduler
scheduler_events = {
	"cron": {
		"0 7 * * *": [
			"neo_dentiq.tasks.send_appointment_reminders",
			"neo_dentiq.tasks.flag_expired_sterile_trays",
		],
		"30 1 * * *": [
			"neo_dentiq.tasks.rescore_no_show_risk",
			"neo_dentiq.tasks.refresh_patient_metrics",
		],
	},
	"daily": [
		"neo_dentiq.tasks.generate_due_recalls",
		"neo_dentiq.tasks.escalate_overdue_recalls",
		"neo_dentiq.tasks.expire_consents",
		"neo_dentiq.tasks.age_insurance_claims",
		"neo_dentiq.tasks.flag_overdue_lab_cases",
		"neo_dentiq.tasks.expire_waitlist_entries",
		"neo_dentiq.tasks.licence_expiry_alerts",
		"neo_dentiq.tasks.payment_plan_reminders",
	],
	"weekly": [
		"neo_dentiq.tasks.recalibrate_no_show_model",
		"neo_dentiq.tasks.sterilizer_validation_alerts",
	],
}

# ---------------------------------------------------------------- permissions
permission_query_conditions = {
	"Patient": "neo_dentiq.permissions.patient_query",
	"Dental Appointment": "neo_dentiq.permissions.appointment_query",
}

has_permission = {
	"Patient": "neo_dentiq.permissions.patient_has_permission",
}

# ---------------------------------------------------------------- dashboards
override_doctype_dashboards = {}

# ---------------------------------------------------------------- misc
treeviews = ["Dental Procedure Category"]

global_search_doctypes = {
	"Default": [
		{"doctype": "Patient", "index": 0},
		{"doctype": "Dental Appointment", "index": 1},
		{"doctype": "Treatment Plan", "index": 2},
		{"doctype": "Clinical Procedure", "index": 3},
	],
}

jinja = {
	"methods": [
		"neo_dentiq.utils.metrics.practice_kpis",
	],
}
