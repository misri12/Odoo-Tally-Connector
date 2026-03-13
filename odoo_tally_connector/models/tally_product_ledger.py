from odoo import api, fields, models


class TallyProductLedger(models.Model):
    _name = "tally.product.ledger"
    _description = "Tally Product / Category Ledger Mapping"
    _rec_name = "ledger_name"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)

    configuration_id = fields.Many2one(
        "tally.configuration",
        string="Configuration",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="configuration_id.company_id",
        store=True,
        readonly=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        help="If set, applies only to this product.",
    )
    category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        help="If product is not set, applies to this category.",
    )

    ledger_name = fields.Char(
        string="Tally Ledger Name",
        required=True,
    )

    mapping_mode = fields.Selection(
        [("product", "Product-wise"), ("category", "Category-wise")],
        string="Mapping Mode",
        compute="_compute_mapping_mode",
        store=True,
    )

    @api.depends("product_id", "category_id")
    def _compute_mapping_mode(self):
        for rec in self:
            if rec.product_id:
                rec.mapping_mode = "product"
            elif rec.category_id:
                rec.mapping_mode = "category"
            else:
                rec.mapping_mode = False

