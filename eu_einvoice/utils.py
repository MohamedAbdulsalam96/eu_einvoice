from enum import Enum
from functools import total_ordering
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from frappe.contacts.doctype.contact.contact import Contact


@total_ordering
class EInvoiceProfile(Enum):
	"""
	Profiles according to Factur-X Specification 1.07.2 page 18.
	'MINIMUM' and 'BASIC WL' are not included because they are not valid tax invoices.
	"""

	BASIC = "BASIC"
	EN16931 = "EN 16931"
	EXTENDED = "EXTENDED"
	XRECHNUNG = "XRECHNUNG"

	def __lt__(self, other):
		# https://stackoverflow.com/a/39269589
		order = [
			EInvoiceProfile.BASIC,
			EInvoiceProfile.EN16931,
			EInvoiceProfile.EXTENDED,
			EInvoiceProfile.XRECHNUNG,
		]
		return order.index(self) < order.index(other)


# Map of EInvoiceProfile to drafthorse schema name
PROFILE_TO_SCHEMA = {
	EInvoiceProfile.BASIC: "FACTUR-X_BASIC",
	EInvoiceProfile.EN16931: "FACTUR-X_EN16931",
	EInvoiceProfile.EXTENDED: "FACTUR-X_EXTENDED",
	EInvoiceProfile.XRECHNUNG: "FACTUR-X_EXTENDED",  # TODO: https://github.com/pretix/python-drafthorse/issues/54
}

# Map of EInvoiceProfile to GuidelineSpecifiedDocumentContextParameter
PROFILE_TO_GUIDELINE = {
	EInvoiceProfile.BASIC: "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic",
	EInvoiceProfile.EN16931: "urn:cen.eu:en16931:2017",
	EInvoiceProfile.EXTENDED: "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended",
	EInvoiceProfile.XRECHNUNG: "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0",
}
GUIDELINE_TO_PROFILE = {v: k for k, v in PROFILE_TO_GUIDELINE.items()}


def get_drafthorse_schema(profile: EInvoiceProfile) -> str:
	"""Return the drafthorse schema name for the given profile."""
	return PROFILE_TO_SCHEMA.get(profile)


def get_guideline(profile: EInvoiceProfile) -> str:
	"""Return the guideline for the given profile."""
	return PROFILE_TO_GUIDELINE.get(profile)


def get_profile(guideline: str) -> EInvoiceProfile:
	"""Return the profile for the given guideline."""
	return GUIDELINE_TO_PROFILE.get(guideline)


def get_full_name(contact: "Contact") -> str:
	return f"{contact.first_name or ''} {contact.last_name or ''}".strip()


def identity(value):
	"""Used for dummy translation"""
	return value
