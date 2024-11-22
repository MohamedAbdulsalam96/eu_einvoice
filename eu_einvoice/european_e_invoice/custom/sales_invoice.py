import re
from decimal import Decimal

import frappe
from drafthorse.models.accounting import ApplicableTradeTax
from drafthorse.models.document import Document
from drafthorse.models.party import TaxRegistration
from drafthorse.models.payment import PaymentTerms
from drafthorse.models.trade import LogisticsServiceCharge
from drafthorse.models.tradelines import LineItem
from frappe import _
from frappe.core.utils import html2text
from frappe.utils.data import flt

from eu_einvoice.common_codes import CommonCodeRetriever

uom_codes = CommonCodeRetriever(
	["urn:xoev-de:kosit:codeliste:rec20_3", "urn:xoev-de:kosit:codeliste:rec21_3"], "C62"
)
payment_means_codes = CommonCodeRetriever(["urn:xoev-de:xrechnung:codeliste:untdid.4461_3"], "ZZZ")
duty_tax_fee_category_codes = CommonCodeRetriever(["urn:xoev-de:kosit:codeliste:untdid.5305_3"], "S")
vat_exemption_reason_codes = CommonCodeRetriever(["urn:xoev-de:kosit:codeliste:vatex_1"], "vatex-eu-ae")


@frappe.whitelist()
def download_xrechnung(invoice_id: str):
	frappe.local.response.filename = f"{invoice_id}.xml"
	frappe.local.response.filecontent = get_einvoice(invoice_id)
	frappe.local.response.type = "download"


def get_einvoice(invoice_id: str) -> bytes:
	invoice = frappe.get_doc("Sales Invoice", invoice_id)
	invoice.check_permission("read")

	seller_address = None
	if invoice.company_address:
		seller_address = frappe.get_doc("Address", invoice.company_address)

	customer_address = None
	if invoice.customer_address:
		customer_address = frappe.get_doc("Address", invoice.customer_address)

	company = frappe.get_doc("Company", invoice.company)

	return get_xml(invoice, company, seller_address, customer_address)


def get_xml(invoice, company, seller_address=None, customer_address=None):
	invoice.run_method("before_einvoice_generation")

	doc = Document()
	doc.context.guideline_parameter.id = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"
	doc.header.id = invoice.name

	# https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred1001.htm
	if invoice.is_return:
		# -- Credit note --
		# Document/message for providing credit information to the relevant party.
		doc.header.type_code = "381"
	elif invoice.amended_from:
		# -- Corrected invoice --
		# Commercial invoice that includes revised information differing from an
		# earlier submission of the same invoice.
		doc.header.type_code = "384"
	else:
		# -- Commercial invoice --
		# Document/message claiming payment for goods or services supplied under
		# conditions agreed between seller and buyer.
		doc.header.type_code = "380"
	doc.header.issue_date_time = invoice.posting_date

	doc.trade.settlement.payee.name = invoice.customer_name
	doc.trade.settlement.currency_code = invoice.currency
	doc.trade.settlement.payment_means.type_code = payment_means_codes.get(
		[("Payment Terms Template", invoice.payment_terms_template)]
		+ [("Mode of Payment", term.mode_of_payment) for term in invoice.payment_schedule]
	)

	doc.trade.agreement.seller.name = invoice.company
	if invoice.company_tax_id:
		try:
			seller_tax_id = validate_vat_id(invoice.company_tax_id.strip())
			seller_vat_scheme = "VA"
		except ValueError:
			seller_tax_id = invoice.company_tax_id.strip()
			seller_vat_scheme = "FC"

		doc.trade.agreement.seller.tax_registrations.add(
			TaxRegistration(
				id=(seller_vat_scheme, seller_tax_id),
			)
		)

	if company.phone_no:
		doc.trade.agreement.seller.contact.telephone.number = company.phone_no
	if company.email:
		doc.trade.agreement.seller.contact.email.address = company.email

	if seller_address:
		doc.trade.agreement.seller.address.line_one = seller_address.address_line1
		doc.trade.agreement.seller.address.line_two = seller_address.address_line2
		doc.trade.agreement.seller.address.postcode = seller_address.pincode
		doc.trade.agreement.seller.address.city_name = seller_address.city
		doc.trade.agreement.seller.address.country_id = frappe.db.get_value(
			"Country", seller_address.country, "code"
		).upper()

	doc.trade.agreement.buyer.name = invoice.customer_name

	if invoice.buyer_reference:
		doc.trade.agreement.buyer_reference = invoice.buyer_reference

	if invoice.po_no:
		doc.trade.agreement.buyer_order.issuer_assigned_id = invoice.po_no

	if invoice.po_date:
		doc.trade.agreement.buyer_order.issue_date_time = invoice.po_date

	if customer_address:
		doc.trade.agreement.buyer.address.line_one = customer_address.address_line1
		doc.trade.agreement.buyer.address.line_two = customer_address.address_line2
		doc.trade.agreement.buyer.address.postcode = customer_address.pincode
		doc.trade.agreement.buyer.address.city_name = customer_address.city
		doc.trade.agreement.buyer.address.country_id = frappe.db.get_value(
			"Country", customer_address.country, "code"
		).upper()

	if invoice.tax_id:
		try:
			customer_tax_id = validate_vat_id(invoice.tax_id.strip())
			customer_vat_scheme = "VA"
		except ValueError:
			customer_tax_id = invoice.tax_id.strip()
			customer_vat_scheme = "FC"

		doc.trade.agreement.buyer.tax_registrations.add(
			TaxRegistration(
				id=(customer_vat_scheme, customer_tax_id),
			)
		)

	for item in invoice.items:
		li = LineItem()
		li.document.line_id = str(item.idx)
		li.product.name = item.item_name
		li.product.seller_assigned_id = item.item_code
		li.product.buyer_assigned_id = item.customer_item_code
		li.product.description = html2text(item.description)
		net_amount = flt(item.net_amount, item.precision("net_amount"))
		li.agreement.net.amount = net_amount

		li.delivery.billed_quantity = (
			flt(item.qty, item.precision("qty")),
			uom_codes.get([("UOM", item.uom)]),
		)

		if item.delivery_note:
			li.delivery.delivery_note.issuer_assigned_id = item.delivery_note
			li.delivery.delivery_note.issue_date_time = frappe.db.get_value(
				"Delivery Note", item.delivery_note, "posting_date"
			)

		li.settlement.trade_tax.type_code = "VAT"
		li.settlement.trade_tax.category_code = duty_tax_fee_category_codes.get(
			[
				("Item Tax Template", item.item_tax_template),
				("Account", item.income_account),
				("Tax Category", invoice.tax_category),
				("Sales Taxes and Charges Template", invoice.taxes_and_charges),
			]
		)
		if li.settlement.trade_tax.category_code._text == "AE":
			# [BR-AE-05] In an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151) is "Reverse charge" the Invoiced item VAT rate (BT-152) shall be 0 (zero).
			li.settlement.trade_tax.rate_applicable_percent = 0
		else:
			li.settlement.trade_tax.rate_applicable_percent = get_item_rate(
				item.item_tax_template, invoice.taxes
			)

		if li.settlement.trade_tax.rate_applicable_percent._value == 0:
			li.settlement.trade_tax.exemption_reason_code = vat_exemption_reason_codes.get(
				[
					("Item Tax Template", item.item_tax_template),
					("Account", item.income_account),
					("Tax Category", invoice.tax_category),
					("Sales Taxes and Charges Template", invoice.taxes_and_charges),
				]
			)

		li.settlement.monetary_summation.total_amount = item.amount
		doc.trade.items.add(li)

	tax_added = False
	for i, tax in enumerate(invoice.taxes):
		if not tax.tax_amount:
			continue

		if tax.charge_type == "Actual":
			service_charge = LogisticsServiceCharge()
			service_charge.description = tax.description
			service_charge.applied_amount = tax.tax_amount
			doc.trade.settlement.service_charge.add(service_charge)
		elif tax.charge_type == "On Net Total":
			trade_tax = ApplicableTradeTax()
			trade_tax.calculated_amount = tax.tax_amount
			trade_tax.type_code = "VAT"
			trade_tax.category_code = duty_tax_fee_category_codes.get(
				[
					("Account", tax.account_head),
					("Tax Category", invoice.tax_category),
					("Sales Taxes and Charges Template", invoice.taxes_and_charges),
				]
			)
			tax_rate = tax.rate or frappe.db.get_value("Account", tax.account_head, "tax_rate") or 0
			trade_tax.rate_applicable_percent = tax_rate

			if len(invoice.taxes) == 1:
				trade_tax.basis_amount = invoice.net_total
			elif hasattr(tax, "net_amount"):
				trade_tax.basis_amount = tax.net_amount
			elif hasattr(tax, "custom_net_amount"):
				trade_tax.basis_amount = tax.custom_net_amount
			elif tax.tax_amount and tax_rate:
				# We don't know the basis amount for this tax, so we try to calculate it
				trade_tax.basis_amount = round(tax.tax_amount / tax_rate * 100, 2)
			else:
				trade_tax.basis_amount = 0

			doc.trade.settlement.trade_tax.add(trade_tax)
			tax_added = True
		elif tax.charge_type == "On Previous Row Amount":
			trade_tax = ApplicableTradeTax()
			trade_tax.basis_amount = invoice.taxes[i - 1].tax_amount
			trade_tax.rate_applicable_percent = tax.rate
			trade_tax.calculated_amount = tax.tax_amount

			if invoice.taxes[i - 1].charge_type == "Actual":
				# VAT for a LogisticsServiceCharge
				trade_tax.type_code = "VAT"
			else:
				# A tax or duty applied on and in addition to existing duties and taxes.
				trade_tax.type_code = "SUR"

			trade_tax.category_code = duty_tax_fee_category_codes.get(
				[
					("Account", tax.account_head),
					("Tax Category", invoice.tax_category),
					("Sales Taxes and Charges Template", invoice.taxes_and_charges),
				]
			)
			doc.trade.settlement.trade_tax.add(trade_tax)
			tax_added = True
		elif tax.charge_type == "On Previous Row Total":
			trade_tax = ApplicableTradeTax()
			trade_tax.basis_amount = invoice.taxes[i - 1].total
			trade_tax.rate_applicable_percent = tax.rate
			trade_tax.calculated_amount = tax.tax_amount

			if invoice.taxes[i - 1].charge_type == "Actual":
				# VAT for a LogisticsServiceCharge
				trade_tax.type_code = "VAT"
			else:
				# A tax or duty applied on and in addition to existing duties and taxes.
				trade_tax.type_code = "SUR"

			trade_tax.category_code = duty_tax_fee_category_codes.get(
				[
					("Account", tax.account_head),
					("Tax Category", invoice.tax_category),
					("Sales Taxes and Charges Template", invoice.taxes_and_charges),
				]
			)
			doc.trade.settlement.trade_tax.add(trade_tax)
			tax_added = True

	if not tax_added:
		trade_tax = ApplicableTradeTax()
		trade_tax.type_code = "VAT"  # [CII-DT-037] - TypeCode shall be 'VAT'
		trade_tax.category_code = duty_tax_fee_category_codes.get(
			[
				("Tax Category", invoice.tax_category),
				("Sales Taxes and Charges Template", invoice.taxes_and_charges),
			]
		)
		trade_tax.basis_amount = invoice.net_total
		trade_tax.rate_applicable_percent = 0
		trade_tax.calculated_amount = 0
		trade_tax.exemption_reason_code = vat_exemption_reason_codes.get(
			[
				("Tax Category", invoice.tax_category),
				("Sales Taxes and Charges Template", invoice.taxes_and_charges),
			]
		)
		doc.trade.settlement.trade_tax.add(trade_tax)

	for ps in invoice.payment_schedule:
		payment_terms = PaymentTerms()
		payment_terms.description = ps.description
		payment_terms.due = ps.due_date

		if len(invoice.payment_schedule) > 1:
			payment_terms.partial_amount.add(
				(ps.payment_amount, None)
			)  # [CII-DT-031] - currencyID should not be present

		if ps.discount and ps.discount_date:
			payment_terms.discount_terms.basis_date_time = ps.discount_date
			if ps.discount_type == "Percentage":
				payment_terms.discount_terms.calculation_percent = ps.discount
			elif ps.discount_type == "Amount":
				payment_terms.discount_terms.actual_amount = ps.discount

		doc.trade.settlement.terms.add(payment_terms)

	doc.trade.settlement.monetary_summation.line_total = invoice.total
	doc.trade.settlement.monetary_summation.charge_total = Decimal("0.00")
	doc.trade.settlement.monetary_summation.allowance_total = invoice.discount_amount
	doc.trade.settlement.monetary_summation.tax_basis_total = invoice.net_total
	doc.trade.settlement.monetary_summation.tax_total = invoice.total_taxes_and_charges
	doc.trade.settlement.monetary_summation.grand_total = invoice.grand_total
	doc.trade.settlement.monetary_summation.prepaid_total = invoice.total_advance
	doc.trade.settlement.monetary_summation.due_amount = invoice.outstanding_amount

	invoice.run_method("after_einvoice_generation", doc)

	return doc.serialize(schema="FACTUR-X_EXTENDED")


def validate_vat_id(vat_id: str) -> tuple[str, str]:
	COUNTRY_CODE_REGEX = r"^[A-Z]{2}$"
	VAT_NUMBER_REGEX = r"^[0-9A-Za-z\+\*\.]{2,12}$"

	country_code = vat_id[:2].upper()
	vat_number = vat_id[2:].replace(" ", "")

	# check vat_number and country_code with regex
	if not re.match(COUNTRY_CODE_REGEX, country_code):
		raise ValueError("Invalid country code")

	if not re.match(VAT_NUMBER_REGEX, vat_number):
		raise ValueError("Invalid VAT number")

	return country_code + vat_number


def validate_doc(doc, event):
	"""Validate the Sales Invoice form."""
	for tax_row in doc.taxes:
		if tax_row.charge_type == "On Item Quantity":
			frappe.msgprint(
				_("{0} row #{1}: Type '{2}' is not supported in e-invoice").format(
					_(doc.meta.get_label("taxes")), tax_row.idx, _(tax_row.charge_type)
				),
				alert=True,
				indicator="orange",
			)


def get_item_rate(item_tax_template: str | None, taxes: list[dict]) -> float | None:
	"""Get the tax rate for an item from the item tax template and the taxes table."""
	if item_tax_template:
		# match the accounts from the taxes table with the rate from the item tax template
		tax_template = frappe.get_doc("Item Tax Template", item_tax_template)
		applicable_accounts = [tax.account_head for tax in taxes if tax.account_head]

		for item_tax in tax_template.taxes:
			if item_tax.tax_type in applicable_accounts:
				return item_tax.tax_rate

	# if only one tax is on net total, return its rate
	tax_rates = [invoice_tax.rate for invoice_tax in taxes if invoice_tax.charge_type == "On Net Total"]
	if len(tax_rates) == 1:
		return tax_rates[0]

	return None


@frappe.whitelist(allow_guest=True)
def download_pdf(
	doctype: str, name: str, format=None, doc=None, no_letterhead=0, language=None, letterhead=None
):
	from facturx import generate_from_binary
	from frappe.utils.print_format import download_pdf as frappe_download_pdf

	frappe_download_pdf(doctype, name, format, doc, no_letterhead, language, letterhead)

	if doctype == "Sales Invoice":
		xml_bytes = get_einvoice(name)
		frappe.local.response.filecontent = generate_from_binary(frappe.local.response.filecontent, xml_bytes)
