import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class TallyConfiguration(models.Model):
    _name = "tally.configuration"
    _description = "Tally Connector Configuration"
    _rec_name = "name"
    _order = "company_id, name"

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    default_sales_ledger = fields.Char(
        string="Default Sales Ledger",
        help="Fallback Tally ledger name for sales income when no product/category mapping is found.",
    )
    default_purchase_ledger = fields.Char(
        string="Default Purchase Ledger",
        help="Fallback Tally ledger name for purchase / expense lines.",
    )
    default_tax_ledger = fields.Char(
        string="Default Tax Ledger",
        help="Fallback Tally ledger name for taxes when no GST mapping is found.",
    )
    enable_bill_allocation = fields.Boolean(
        string="Enable Bill Allocation",
        default=True,
        help="If enabled, payment vouchers will include BILLALLOCATIONS for invoice settlement.",
    )

    product_ledger_ids = fields.One2many(
        "tally.product.ledger",
        "configuration_id",
        string="Product / Category Ledger Mapping",
    )
    tax_mapping_ids = fields.One2many(
        "tally.tax.mapping",
        "configuration_id",
        string="GST Tax Mapping",
    )
    payment_mapping_ids = fields.One2many(
        "tally.payment.mapping",
        "configuration_id",
        string="Payment Method Mapping",
    )

    _sql_constraints = [
        (
            "company_uniq",
            "unique(company_id)",
            "Only one Tally configuration is allowed per company.",
        )
    ]

    @api.model
    def get_for_company(self, company):
        """Return the configuration for a given company, or False."""
        if not company:
            company = self.env.company
        return self.search([("company_id", "=", company.id)], limit=1)

