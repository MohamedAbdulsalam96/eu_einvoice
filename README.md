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

## Setup

E-invoices rely on common codes that describe the content of the invoice. E.g. "C62" is used for the UOM "One" and "ZZZ" is used for a mutually agreed mode of payment.

Common codes are part of a code list. You'll need to import the code lists and map the codes you need to the corresponding ERPNext entities. Please use the "Import Genericode" button in **Code List** and paste the URL linked below.

Code List | Mapped DocType | Default Value
----------|----------------|--------------
[UNTDID 4461 Payment means code](https://www.xrepository.de/api/xrepository/urn:xoev-de:xrechnung:codeliste:untdid.4461_3:technischerBestandteilGenericode) | Payment Terms Template, Mode of Payment | ZZZ
[Codes for Units of Measure Used in International Trade](https://www.xrepository.de/api/xrepository/urn:xoev-de:kosit:codeliste:rec20_3:technischerBestandteilGenericode) | UOM | C62
[Codes for Passengers, Types of Cargo, Packages and Packaging Materials](https://www.xrepository.de/api/xrepository/urn:xoev-de:kosit:codeliste:rec21_3:technischerBestandteilGenericode) (optional) | UOM | C62
[Codes for Duty Tax and Fee Categories](https://www.xrepository.de/api/xrepository/urn:xoev-de:kosit:codeliste:untdid.5305_3:technischerBestandteilGenericode) | Item Tax Template, Account, Tax Category, Sales Taxes and Charges Template | S
[VAT exemption reason code list](https://www.xrepository.de/api/xrepository/urn:xoev-de:kosit:codeliste:vatex_1:technischerBestandteilGenericode) | Item Tax Template, Account, Tax Category, Sales Taxes and Charges Template | vatex-eu-ae

For example, let's say your standard **Payment Terms Template** is "Bank Transfer, 30 days". You'll need to find the suitable **Common Code** for bank transfers within the **Code List** "UNTDID.4461". In this case, the code is "58". Then you add a row to the _Applies To_ table, select "Payment Terms Template" as the _Link Document Type_ and "Bank Transfer, 30 days" as the _Link Name_. If you now create an Invoice with this **Payment Terms Template**, the eInvoice will contain the code "58" for the payment means, signalling that the payment should done via bank transfer.

The retrieval of codes goes from the most specific to the most general. E.g. for determining the VAT type of a line item, we first look for a code using the specific item's _Item Tax Template_ and _Income Account_, then fall back to the code for the invoice's _Tax Category_ or _Sales Taxes and Charges Template_.

### Buyer Reference (German: Leitweg-ID)

If you work with government customers or similar large organizations, you might need to specify their _Buyer Reference_ in the eInvoice. This is done by setting the _Buyer Reference_ field in the **Sales Invoice**. You can already fill this field in the **Customer** master data or the **Sales Order**.

## Usage

### Sales Invoice

To create a new eInvoice, open a **Sales Invoice** and click on "..." > "Download eInvoice". This will generate an XML file that you can send to your customer.

When you open the print preview of the **Sales Invoice** and click on "PDF", the generated PDF file will have the e-invoice XML embedded. 

> [!TIP]
> You can test both XML and PDF+XML files by re-importing them, using the **E Invoice Import** DocType.

The following fields of the **Sales Invoice** are currently considered for the eInvoice:

- Invoice type (credit note, corrected invoice, commercial invoice)
- Invoice number
- Invoice date
- Due date
- From date
- To date
- Language
- Currency
- Company
    - Phone No
    - Email
    - Fax
- Company Name
- Company Address
    - Address Line 1
    - Address Line 2
    - Postcode
    - City
    - Country
- Company Contact Person
    - Full Name
    - Email Address (takes precedence over Company > Email)
    - Phone (takes precedence over Company > Phone No)
    - Department
- Company Tax ID
- Customer Name
- Buyer Reference (fetched from **Sales Order** or **Customer**)
- Customer Address
    - Address Line 1
    - Address Line 2
    - Postcode
    - City
    - Country
- Contact Email
- Contact Mobile (takes precedence over Contact Person > Phone)
- Contact Person
    - Full Name
    - Phone
    - Department
- Customer's Purchase Order
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
- Terms and Conditions Details (converted to markdown)
- Incoterm and named place
- Payment Schedule
    - Description
    - Due date
    - Amount
    - Discount Type (must be "Percentage")
    - Discount
    - Discount Date
- Sales Taxs and Charges
    - The _Charge Type_ "Actual" is used as logistics or service charges.
    - For _Charge Type_ "On Net Total", the taxable amount is calculated as `tax_amount / rate * 100`, if the rate is available in the tax row or in the corresponding Account [1].
    - The _Charge Type_ "On Item Quantity" is not supported.
- Total
- Discount Amount
- Net Total
- Total Taxes and Charges
- Grand Total
- Total Advance
- Outstanding Amount

[1] The correct taxable amount is only available starting from ERPNext v16. For earlier versions we currently have to approximate it, which comes with a small error margin.

### Purchase Invoice

To import a new eInvoice, create a new **E Invoice Import** and upload the XML or PDF file.

The imported XML is validated against the "EN16931 CII" and "XRechnung CII" schematron. You'll see the validation errors in the import's _Validation_ tab. It is still possible to import an invoice, even if there are formal validation errors.

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

## Validation

You can upload an XML invoice file to https://www.itb.ec.europa.eu/invoice/upload and validate it as "CII Invoice CML".

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

    Used to create and parse XML invoices.

- [factur-x](https://pypi.org/project/factur-x/) by Alexis de Lattre, released unser a BSD License

    Used to extract XML data from PDF files, and to create PDF files with embedded XML.

- [SaxonC](https://pypi.org/project/saxonche/) by Saxonica

    Used for XSL transformation (validate XML against schematron).

- [lxml](https://github.com/lxml/lxml) by Infrae

    Used for general XML parsing.

- [SchXslt](https://github.com/schxslt/schxslt) by David Maus

    Used to convert Schematron files to XSL.

## Sponsors

Many thanks to the following companies for sponsoring the initial development of this app:

- aepfel+birnen IT GmbH
- axessio Hausverwaltung GmbH
- Burkhard Baumsteigtechnik GmbH & Co. KG
- DriveCon GmbH
- ibb testing gmbh
- itsdave GmbH
- iXGate UG
- Kautenburger IT GmbH
- MERECS Engineering GmbH
- voidsy GmbH
- … and many more

> [!NOTE]
> We only list companies that have explicitly agreed to have their name published here. If you want to be listed here too, please send us a short note by email.

## License

Copyright (C) 2024 ALYF GmbH

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or(at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
