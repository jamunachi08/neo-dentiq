"""ZATCA (Saudi) Phase-2 e-invoicing hook: TLV QR payload and hash chain."""
import base64
import hashlib

import frappe
from frappe.utils import flt


def _tlv(tag, value):
	raw = str(value).encode("utf-8")
	return bytes([tag, len(raw)]) + raw


def generate_qr(sales_invoice):
	"""Build the base64 TLV QR string mandated for simplified tax invoices."""
	si = frappe.get_doc("Sales Invoice", sales_invoice)
	company = frappe.get_cached_doc("Company", si.company)
	vat_number = company.tax_id or ""
	vat_amount = flt(sum(t.tax_amount for t in si.taxes or []))
	payload = (
		_tlv(1, company.company_name)
		+ _tlv(2, vat_number)
		+ _tlv(3, si.posting_date.isoformat() if hasattr(si.posting_date, "isoformat")
		       else str(si.posting_date))
		+ _tlv(4, f"{flt(si.grand_total):.2f}")
		+ _tlv(5, f"{vat_amount:.2f}")
	)
	return base64.b64encode(payload).decode()


def invoice_hash(sales_invoice, previous_hash=None):
	"""Chained SHA-256 invoice hash (PIH) for the clearance model."""
	si = frappe.get_doc("Sales Invoice", sales_invoice)
	canonical = f"{si.name}|{si.posting_date}|{flt(si.grand_total):.2f}|{si.customer}"
	if previous_hash:
		canonical = previous_hash + "|" + canonical
	return base64.b64encode(hashlib.sha256(canonical.encode()).digest()).decode()


def attach_to_invoice(doc, method=None):
	if not frappe.db.get_single_value("Neo Dentiq Settings", "enable_zatca_einvoice"):
		return
	if doc.doctype != "Sales Invoice" or doc.docstatus != 1:
		return
	try:
		doc.db_set("neo_dentiq_zatca_qr", generate_qr(doc.name), update_modified=False)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ZATCA QR")
