from .utils import identity as _


def get_custom_fields():
	return {
		"Purchase Invoice": [
			{
				"fieldname": "e_invoice_import",
				"label": _("E Invoice Import"),
				"insert_after": "bill_no",
				"fieldtype": "Link",
				"options": "E Invoice Import",
				"read_only": 1,
			}
		],
		"Customer": [
			{
				"fieldname": "buyer_reference",
				"label": _("Buyer Reference"),
				"insert_after": "language",
				"fieldtype": "Data",
			},
		],
		"Sales Order": [
			{
				"fieldname": "buyer_reference",
				"label": _("Buyer Reference"),
				"insert_after": "tax_id",
				"fieldtype": "Data",
				"fetch_from": "customer.buyer_reference",
				"fetch_if_empty": 1,
			},
		],
		"Sales Invoice": [
			{
				"fieldname": "buyer_reference",
				"label": _("Buyer Reference"),
				"insert_after": "tax_id",
				"fieldtype": "Data",
				"fetch_from": "customer.buyer_reference",
				"fetch_if_empty": 1,
			},
			{
				"fieldname": "e_invoice_validation_section",
				"label": _("E Invoice Validation"),
				"insert_after": "remarks",
				"fieldtype": "Section Break",
				"collapsible": 1,
			},
			{
				"fieldname": "correct_european_invoice",
				"label": _("Correct European Invoice"),
				"insert_after": "e_invoice_validation_section",
				"fieldtype": "Check",
				"read_only": 1,
				"print_hide": 1,
			},
			{
				"fieldname": "correct_german_federal_administration_invoice",
				"label": _("Correct German Federal Administration Invoice"),
				"insert_after": "correct_european_invoice",
				"fieldtype": "Check",
				"read_only": 1,
				"print_hide": 1,
			},
			{
				"fieldname": "validation_errors",
				"label": _("Validation Errors"),
				"insert_after": "correct_german_federal_administration_invoice",
				"fieldtype": "Text",
				"read_only": 1,
				"print_hide": 1,
			},
		],
	}
