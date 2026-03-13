import logging
from collections import defaultdict

from lxml import etree

from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class TallyXMLGenerator:
    """High performance Tally XML generator."""

    def __init__(self, env):
        self.env = env

    def generate(self, configuration, invoices, payments):
        """Return a full Tally-compatible XML string."""
        _logger.info(
            "Generating Tally XML for company %s: %s invoices, %s payments",
            configuration.company_id.display_name,
            len(invoices),
            len(payments),
        )

        ledger_set = set()
        tax_mapping = self._load_tax_mapping(configuration)
        product_mapping = self._load_product_mapping(configuration)
        payment_mapping = self._load_payment_mapping(configuration)

        envelope = etree.Element("ENVELOPE")

        header = etree.SubElement(envelope, "HEADER")
        tally_request = etree.SubElement(header, "TALLYREQUEST")
        tally_request.text = "Import Data"

        body = etree.SubElement(envelope, "BODY")
        importdata = etree.SubElement(body, "IMPORTDATA")

        request_desc = etree.SubElement(importdata, "REQUESTDESC")
        report_name = etree.SubElement(request_desc, "REPORTNAME")
        report_name.text = "Vouchers"

        request_data = etree.SubElement(importdata, "REQUESTDATA")

        self._generate_ledger_and_voucher_nodes(
            request_data,
            configuration,
            invoices,
            payments,
            ledger_set,
            tax_mapping,
            product_mapping,
            payment_mapping,
        )

        self._prepend_ledger_masters(envelope, ledger_set, configuration)

        xml_bytes = etree.tostring(
            envelope,
            xml_declaration=True,
            encoding="utf-8",
        )
        return xml_bytes.decode("utf-8")

    # ------------------------------------------------------------------
    # Load helpers
    # ------------------------------------------------------------------

    def _load_tax_mapping(self, configuration):
        mapping = {}
        for rec in configuration.tax_mapping_ids:
            mapping[rec.tax_id.id] = rec.tally_ledger_name
        return mapping

    def _load_product_mapping(self, configuration):
        by_product = {}
        by_category = {}
        for rec in configuration.product_ledger_ids:
            if rec.product_id:
                by_product[rec.product_id.id] = rec.ledger_name
            elif rec.category_id:
                by_category[rec.category_id.id] = rec.ledger_name
        return {"product": by_product, "category": by_category}

    def _load_payment_mapping(self, configuration):
        mapping = {}
        for rec in configuration.payment_mapping_ids:
            mapping[rec.journal_id.id] = rec.tally_ledger_name
        return mapping

    # ------------------------------------------------------------------
    # Ledger master generation
    # ------------------------------------------------------------------

    def _prepend_ledger_masters(self, envelope, ledger_set, configuration):
        body = envelope.find("./BODY")
        if body is None:
            return

        importdata_master = etree.Element("IMPORTDATA")
        request_desc_master = etree.SubElement(importdata_master, "REQUESTDESC")
        report_name_master = etree.SubElement(request_desc_master, "REPORTNAME")
        report_name_master.text = "Masters"

        request_data_master = etree.SubElement(importdata_master, "REQUESTDATA")

        for ledger_name in sorted(ledger_set):
            tally_message = etree.SubElement(request_data_master, "TALLYMESSAGE")
            ledger = etree.SubElement(
                tally_message, "LEDGER", NAME=ledger_name, ACTION="Create"
            )
            etree.SubElement(ledger, "NAME").text = ledger_name
            etree.SubElement(ledger, "PARENT").text = "Sundry Debtors"

        body.insert(0, importdata_master)

    # ------------------------------------------------------------------
    # Voucher generation
    # ------------------------------------------------------------------

    def _generate_ledger_and_voucher_nodes(
        self,
        request_data,
        configuration,
        invoices,
        payments,
        ledger_set,
        tax_mapping,
        product_mapping,
        payment_mapping,
    ):
        invoice_sort_field = "date" if "date" in invoices._fields else "invoice_date"
        invoices = invoices.sorted(invoice_sort_field)
        payments = payments.sorted("date" if "date" in payments._fields else "payment_date")

        invoices.mapped("invoice_line_ids.product_id")
        invoices.mapped("partner_id")
        invoices.mapped("line_ids.tax_ids")

        for inv in invoices:
            self._add_invoice_voucher(
                request_data,
                inv,
                configuration,
                ledger_set,
                tax_mapping,
                product_mapping,
            )

        for pay in payments:
            self._add_payment_voucher(
                request_data,
                pay,
                configuration,
                ledger_set,
                payment_mapping,
            )

    def _add_invoice_voucher(
        self,
        request_data,
        inv,
        configuration,
        ledger_set,
        tax_mapping,
        product_mapping,
    ):
        company = configuration.company_id
        if inv.company_id != company:
            return

        tally_message = etree.SubElement(request_data, "TALLYMESSAGE")
        voucher_type = self._get_invoice_voucher_type(inv)
        voucher = etree.SubElement(
            tally_message,
            "VOUCHER",
            VCHTYPE=voucher_type,
            ACTION="Create",
        )

        etree.SubElement(voucher, "DATE").text = (
            inv.invoice_date or inv.date or inv.create_date.date()
        ).strftime("%Y%m%d")

        etree.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
        etree.SubElement(voucher, "VOUCHERNUMBER").text = inv.name or ""
        etree.SubElement(voucher, "PARTYNAME").text = inv.partner_id.name or ""
        etree.SubElement(voucher, "PARTYLEDGERNAME").text = inv.partner_id.name or ""

        ledger_set.add(inv.partner_id.name or "")
        ledger_line = etree.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        etree.SubElement(ledger_line, "LEDGERNAME").text = inv.partner_id.name or ""
        etree.SubElement(ledger_line, "ISDEEMEDPOSITIVE").text = "No"
        etree.SubElement(
            ledger_line,
            "AMOUNT",
        ).text = self._format_amount(inv.amount_total_signed)

        for line in inv.invoice_line_ids:
            ledger_name = self._map_product_ledger(line, configuration, product_mapping)
            ledger_set.add(ledger_name)

            line_elt = etree.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            etree.SubElement(line_elt, "LEDGERNAME").text = ledger_name
            etree.SubElement(line_elt, "ISDEEMEDPOSITIVE").text = "Yes"
            etree.SubElement(line_elt, "AMOUNT").text = self._format_amount(
                -line.price_subtotal
            )

            inv_list = etree.SubElement(line_elt, "ALLINVENTORYENTRIES.LIST")
            etree.SubElement(inv_list, "STOCKITEMNAME").text = line.product_id.display_name
            etree.SubElement(inv_list, "ACTUALQTY").text = str(line.quantity)
            etree.SubElement(inv_list, "BILLEDQTY").text = str(line.quantity)
            rate = line.price_unit
            etree.SubElement(inv_list, "RATE").text = self._format_amount(rate)
            etree.SubElement(inv_list, "AMOUNT").text = self._format_amount(
                -line.price_subtotal
            )

        tax_line_map = defaultdict(float)
        for line in inv.invoice_line_ids:
            for tax in line.tax_ids:
                tax_line_map[tax.id] += line.price_subtotal * tax.amount / 100.0

        for tax_id, amount in tax_line_map.items():
            ledger_name = tax_mapping.get(tax_id) or configuration.default_tax_ledger
            if not ledger_name:
                continue
            ledger_set.add(ledger_name)
            tax_line_elt = etree.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            etree.SubElement(tax_line_elt, "LEDGERNAME").text = ledger_name
            etree.SubElement(tax_line_elt, "ISDEEMEDPOSITIVE").text = "Yes"
            etree.SubElement(tax_line_elt, "AMOUNT").text = self._format_amount(-amount)

    def _add_payment_voucher(
        self,
        request_data,
        pay,
        configuration,
        ledger_set,
        payment_mapping,
    ):
        company = configuration.company_id
        if pay.company_id != company:
            return

        journal_ledger = payment_mapping.get(pay.journal_id.id) or pay.journal_id.name
        ledger_set.add(journal_ledger)

        voucher_type = "Receipt" if pay.payment_type == "inbound" else "Payment"

        tally_message = etree.SubElement(request_data, "TALLYMESSAGE")
        voucher = etree.SubElement(
            tally_message, "VOUCHER", VCHTYPE=voucher_type, ACTION="Create"
        )

        date_field = getattr(pay, "date", False) or getattr(pay, "payment_date", False)
        etree.SubElement(voucher, "DATE").text = date_field.strftime("%Y%m%d")
        etree.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
        etree.SubElement(voucher, "VOUCHERNUMBER").text = pay.name or ""
        etree.SubElement(voucher, "PARTYNAME").text = pay.partner_id.name or ""
        etree.SubElement(voucher, "PARTYLEDGERNAME").text = pay.partner_id.name or ""

        amount = pay.amount if pay.payment_type == "inbound" else -pay.amount

        bank_line = etree.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        etree.SubElement(bank_line, "LEDGERNAME").text = journal_ledger
        etree.SubElement(bank_line, "ISDEEMEDPOSITIVE").text = (
            "No" if pay.payment_type == "inbound" else "Yes"
        )
        etree.SubElement(bank_line, "AMOUNT").text = self._format_amount(amount)

        party_ledger_name = pay.partner_id.name or ""
        ledger_set.add(party_ledger_name)

        party_line = etree.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        etree.SubElement(party_line, "LEDGERNAME").text = party_ledger_name
        etree.SubElement(party_line, "ISDEEMEDPOSITIVE").text = (
            "Yes" if pay.payment_type == "inbound" else "No"
        )
        etree.SubElement(party_line, "AMOUNT").text = self._format_amount(-amount)

        if configuration.enable_bill_allocation:
            self._add_bill_allocations(pay, party_line)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_invoice_voucher_type(self, inv):
        if inv.move_type == "out_invoice":
            return "Sales"
        if inv.move_type == "in_invoice":
            return "Purchase"
        if inv.move_type == "out_refund":
            return "Credit Note"
        if inv.move_type == "in_refund":
            return "Debit Note"
        return "Journal"

    def _map_product_ledger(self, line, configuration, product_mapping):
        product = line.product_id
        ledger = None
        if product and product.id in product_mapping["product"]:
            ledger = product_mapping["product"][product.id]
        elif product and product.categ_id and product.categ_id.id in product_mapping["category"]:
            ledger = product_mapping["category"][product.categ_id.id]

        if not ledger:
            if line.move_id.move_type in ("out_invoice", "out_refund"):
                ledger = configuration.default_sales_ledger
            else:
                ledger = configuration.default_purchase_ledger

        return ledger or "Sales"

    def _add_bill_allocations(self, payment, party_line_elt):
        move_lines = payment.move_id.line_ids.filtered(
            lambda ml: ml.account_id.internal_type in ("receivable", "payable")
        )

        for ml in move_lines:
            for partial in ml.matched_debit_ids | ml.matched_credit_ids:
                inv_line = (
                    partial.debit_move_id
                    if partial.debit_move_id.move_id.move_type
                    in ("out_invoice", "in_invoice", "out_refund", "in_refund")
                    else partial.credit_move_id
                )
                inv = inv_line.move_id
                amount = float_round(partial.amount, precision_digits=2)
                if not inv.name:
                    continue

                alloc = etree.SubElement(party_line_elt, "BILLALLOCATIONS.LIST")
                etree.SubElement(alloc, "NAME").text = inv.name
                etree.SubElement(alloc, "BILLTYPE").text = "Agst Ref"
                etree.SubElement(alloc, "AMOUNT").text = self._format_amount(
                    -amount if payment.payment_type == "inbound" else amount
                )

    def _format_amount(self, amount):
        return "%.2f" % float_round(amount, precision_digits=2)