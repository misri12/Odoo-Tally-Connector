from odoo import fields, models


class TallyTaxMapping(models.Model):
    _name = "tally.tax.mapping"
    _description = "Tally GST Tax Mapping"
    _rec_name = "tax_id"
    _order = "company_id, tax_id"

    GST_TYPES = [
        ("cgst", "CGST"),
        ("sgst", "SGST"),
        ("igst", "IGST"),
        ("cess", "CESS"),
    ]

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    configuration_id = fields.Many2one(
        "tally.configuration",
        string="Tally Configuration",
        ondelete="cascade",
    )

    tax_id = fields.Many2one(
        "account.tax",
        string="Odoo Tax",
        required=True,
        domain=[("type_tax_use", "in", ("sale", "purchase", "none"))],
    )
    tally_ledger_name = fields.Char(
        string="Tally Ledger Name", required=True
    )
    gst_type = fields.Selection(
        GST_TYPES,
        string="GST Type",
        required=True,
    )

    _sql_constraints = [
        (
            "tax_company_uniq",
            "unique(company_id, tax_id)",
            "Each tax can only be mapped once per company.",
        )
    ]

