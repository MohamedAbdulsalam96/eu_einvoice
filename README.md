## European e-Invoice

Create and import e-invoices with ERPNext.

In particular, this app supports reading and writing electronic invoices according to the following standards:

- ZUGFeRD
- XRechnung
- Factur-X
- UN/CEFACT Cross-Industry-Invoice (CII)
- EN16931

This app cannot read or write UBL invoices. It also does not provide any special way of sending or receiving e-invoices (e.g. Peppol). Instead, it focuses on the conversion between ERPNext's internal data model and the XML format of the above standards.

> [!WARNING]
> This app is under active development and should **not** yet be used in production environments. Things can **break and change at any time**.

## Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app eu_einvoice
```

## Usage

### Sales Invoice

To create a new eInvoice, open a **Sales Invoice** and click on "..." > "Download eInvoice".

For german government customers, the "Leitwegs-ID" should be entered into the field _Customer's Purchase Order_ of the **Sales Invoice**. This way it will show up in the XML's `BuyerReference` element.

The following fields of the **Sales Invoice** are currently considered for the eInvoice:

- Invoice type (credit note, corrected invoice, commercial invoice)
- Invoice number
- Invoice date
- Due date
- Language
- Currency
- Company Name
- Company Address
- Company Tax ID
- Company Phone (fetched from **Company**)
- Company Email (fetched from **Company**)
- Customer Name
- Customer Address
- Customer's Purchase Order (doubles as "Leitwegs-ID" for german government customers)
- Customer's Purchase Order Date
- Customer's Tax ID
- Items:
    - Item Name
    - Description
    - Company's Item Code
    - Customer's Item Code
    - Delivery Note number and date
    - Quantity + Unit
    - Rate
    - Net Amount
    - Amount
- Payment terms:
    - Description
    - Due date
    - Amount
    - Early Payment Discount
        - Percentage or Amount
        - Due date
- Sales Taxs and Charges
    - The _Charge Type_ "Actual" is used as logistics or service charges.
    - For _Charge Type_ "On Net Total", the taxable amount is calculated as `tax_amount / rate * 100`, if the rate is available in the tax row or in the corresponding Account.
    - The _Charge Type_ "On Item Quantity" is not supported.
- Total
- Discount Amount
- Net Total
- Total Taxes and Charges
- Grand Total
- Total Advance
- Outstanding Amount

### Purchase Invoice

To import a new eInvoice, create a new **E Invoice Import** and upload the XML or PDF file.

Taxes are mapped to "Actual" charges in the **Purchase Invoice**, so that ERPNext does not try to recalculate them.

## Add your custom logic

This app provides hooks to add custom logic to the eInvoice creation process:

- `before_einvoice_generation`

    Called right before the eInvoice is generated. The hook function receives the **Sales Invoice** as an argument and can modify it.

- `after_einvoice_generation`

    Called right after the eInvoice is generated. The hook function receives the **Sales Invoice** and the generated eInvoice as arguments.

For example, your `myapp/hooks.py` could look like this:

```python
doc_events = {
	"Sales Invoice": {
		"before_einvoice_generation": "myapp.einvoice.before_einvoice_generation",
		"after_einvoice_generation": "myapp.einvoice.after_einvoice_generation",
	}
}
```

And your `myapp/einvoice.py` like this:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from drafthorse.models.document import Document
    from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


def before_einvoice_generation(doc: "SalesInvoice", event: str):
    """Modify the Sales Invoice object before generating the eInvoice."""
    doc.customer_name = "Special Customer Name, only for eInvoices"


def after_einvoice_generation(doc: "SalesInvoice", event: str, einvoice: "Document"):
    """Modify the generated eInvoice after it was created."""
    einvoice.trade.agreement.buyer.name = "Special Customer Name, only for eInvoices"
```

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/eu_einvoice
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.

### Dependencies

- [drafthorse](https://pypi.org/project/drafthorse/) by Raphael Michel, released under the Apache License 2.0

    Used to create and parse XML invoices

- [factur-x](https://pypi.org/project/factur-x/) by Alexis de Lattre, released unser a BSD License

    Used to extract XML data from a PDF file

## License

Copyright (C) 2024 ALYF GmbH

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or(at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
