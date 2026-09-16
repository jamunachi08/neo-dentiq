# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class DentalProcedure(Document):
	def validate(self):
		self.set_abbr()

	def after_insert(self):
		if not self.item:
			self.create_item()

	def set_abbr(self):
		if self.abbr:
			return
		words = [w for w in (self.procedure_name or "").split() if w]
		self.abbr = "".join(w[0] for w in words[:3]).upper()

	def create_item(self):
		"""Every procedure is a non-stock ERPNext Item so it can be invoiced natively."""
		group = frappe.db.get_value(
			"Dental Procedure Category", self.category, "item_group") or "Dental Services"
		if not frappe.db.exists("Item Group", group):
			group = "Dental Services"
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": f"DP-{self.name}"[:140],
			"item_name": self.procedure_name[:140],
			"item_group": group,
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
			"is_purchase_item": 0,
			"include_item_in_manufacturing": 0,
			"description": self.patient_description or self.procedure_name,
		})
		if self.income_account:
			item.append("item_defaults", {
				"company": frappe.db.get_single_value("Neo Dentiq Settings", "default_company"),
				"income_account": self.income_account,
			})
		item.insert(ignore_permissions=True)
		self.db_set("item", item.name)
		if self.standard_rate:
			price_list = frappe.db.get_single_value("Neo Dentiq Settings", "default_price_list") \
				or "Standard Selling"
			frappe.get_doc({
				"doctype": "Item Price", "item_code": item.name,
				"price_list": price_list, "price_list_rate": self.standard_rate,
			}).insert(ignore_permissions=True)
