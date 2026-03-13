from odoo import models, fields


class TallyXMLTag(models.Model):
    _name = "tally.xml.tag"
    _description = "Tally XML Tag"
    _rec_name = "name"
    _order = "name"

    name = fields.Char(
        string="Label",
        required=True,
        help="Friendly label used in Odoo UI."
    )

    xml_tag = fields.Char(
        string="XML Tag",
        required=True,
        help="Exact XML tag used in Tally (example: LEDGERNAME, DATE, AMOUNT)."
    )

    description = fields.Text(
        string="Description",
        help="Optional explanation of this XML tag."
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    _sql_constraints = [
        (
            "xml_tag_unique",
            "unique(xml_tag)",
            "XML Tag must be unique!"
        )
    ]


