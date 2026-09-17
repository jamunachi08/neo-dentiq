import frappe
from frappe.utils import flt


def check_reorder(doc, method=None):
	"""Raise a Material Request when a clinical consumable drops below reorder level."""
	item = doc.item_code
	defaults = frappe.db.get_value(
		"Item Reorder", {"parent": item},
		["warehouse_reorder_level", "warehouse_reorder_qty", "warehouse"], as_dict=True)
	if not defaults or flt(doc.qty_after_transaction) > flt(defaults.warehouse_reorder_level):
		return
	exists = frappe.db.exists("Material Request Item", {
		"item_code": item, "docstatus": ["<", 2],
	})
	if exists:
		return
	group = frappe.db.get_value("Item", item, "item_group")
	if group not in ("Dental Consumables", "Dental Implants", "Dental Materials",
	                 "Dental Pharmacy"):
		return
	frappe.get_doc({
		"doctype": "Material Request",
		"material_request_type": "Purchase",
		"transaction_date": frappe.utils.nowdate(),
		"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
		"company": frappe.db.get_single_value("Neo Dentiq Settings", "default_company"),
		"items": [{
			"item_code": item,
			"qty": flt(defaults.warehouse_reorder_qty) or 10,
			"warehouse": defaults.warehouse,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
		}],
	}).insert(ignore_permissions=True)
