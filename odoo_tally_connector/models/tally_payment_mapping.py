from odoo import fields, models


class TallyPaymentMapping(models.Model):
    _name = "tally.payment.mapping"
    _description = "Tally Payment Method Mapping"
    _rec_name = "journal_id"
    _order = "company_id, journal_id"

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

    journal_id = fields.Many2one(
        "account.journal",
        string="Payment Journal",
        required=True,
        domain=[("type", "in", ("cash", "bank"))],
    )
    tally_ledger_name = fields.Char(
        string="Tally Ledger Name",
        required=True,
        help="Name of the Cash/Bank ledger in Tally.",
    )

    _sql_constraints = [
        (
            "journal_company_uniq",
            "unique(company_id, journal_id)",
            "Each journal can only be mapped once per company.",
        )
    ]

