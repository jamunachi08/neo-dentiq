# Copyright (c) 2026, Neo Dentiq and contributors
# For license information, please see license.txt

from frappe.utils.nestedset import NestedSet


class DentalProcedureCategory(NestedSet):
	nsm_parent_field = "parent_dental_procedure_category"

	def on_update(self):
		super().update_nsm_model()
