from odoo import api, fields, models


class TallyFieldMapping(models.Model):
    _name = "tally.field.mapping"
    _description = "Tally Field Mapping"
    _rec_name = "name"
    _order = "sequence, id"

    name = fields.Char(required=True, string="Name")
    sequence = fields.Integer(default=10)

    xml_tag_id = fields.Many2one(
        "tally.xml.tag",
        required=True,
        string="XML Tag",
    )

    model_id = fields.Many2one(
        "ir.model",
        string="Odoo Model",
        required=True,
        ondelete="cascade",
        help="Model from which to read the value (e.g. account.move).",
    )
    odoo_field = fields.Char(
        string="Field Name",
        required=True,
        help="Python-style field expression starting from the record "
        "(e.g. partner_id.name, amount_total_signed).",
    )
    eval_python = fields.Boolean(
        string="Evaluate as Python expression",
        help="If enabled, the expression is evaluated as Python code "
        "with 'record' in context instead of using dot-path lookup.",
    )

    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.constrains("odoo_field")
    def _check_field_not_empty(self):
        for rec in self:
            if not rec.odoo_field or not rec.odoo_field.strip():
                raise ValueError("Odoo field path cannot be empty.")

