import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TallyGenerateXML(models.TransientModel):
    _name = "tally.generate.xml"
    _description = "Generate Tally XML"
    _rec_name = "configuration_id"

    configuration_id = fields.Many2one(
        "tally.configuration",
        string="Configuration",
        required=True,
        domain=lambda self: [("company_id", "=", self.env.company.id)],
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="configuration_id.company_id",
        readonly=True,
    )

    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")

    # -----------------------------
    # DOCUMENT SELECTION
    # -----------------------------

    invoice_ids = fields.Many2many(
        "account.move",
        "tally_generate_invoice_rel",
        "wizard_id",
        "move_id",
        string="Invoices / Bills",
        domain=[
            ("move_type", "in", ("out_invoice", "in_invoice", "out_refund", "in_refund")),
            ("state", "=", "posted"),
        ],
        default=lambda self: self.env["account.move"].browse([]),
    )

    payment_ids = fields.Many2many(
        "account.payment",
        "tally_generate_payment_rel",
        "wizard_id",
        "payment_id",
        string="Payments",
        domain=[("state", "=", "posted")],
        default=lambda self: self.env["account.payment"].browse([]),
    )

    # -----------------------------
    # EXPORT OPTIONS
    # -----------------------------

    export_customer_invoices = fields.Boolean(default=True)
    export_vendor_bills = fields.Boolean(default=True)
    export_credit_notes = fields.Boolean(default=True)
    export_debit_notes = fields.Boolean(default=True)
    export_customer_payments = fields.Boolean(default=True)
    export_vendor_payments = fields.Boolean(default=True)

    # -----------------------------
    # DATE DOMAIN
    # -----------------------------

    def _compute_invoice_domain(self):
        domain = [
            ("company_id", "=", self.env.company.id),
            ("state", "=", "posted"),
        ]

        move_types = []
        if self.export_customer_invoices:
            move_types.append("out_invoice")
        if self.export_vendor_bills:
            move_types.append("in_invoice")
        if self.export_credit_notes:
            move_types.append("out_refund")
        if self.export_debit_notes:
            move_types.append("in_refund")

        if move_types:
            domain.append(("move_type", "in", tuple(move_types)))

        # Use a robust date field for filtering:
        # - `account.move.date` exists on standard Odoo and is always set for posted moves.
        # - `invoice_date` may be empty depending on version/migration/user input.
        date_field = "date" if "date" in self.env["account.move"]._fields else "invoice_date"

        if self.date_from:
            domain.append((date_field, ">=", self.date_from))

        if self.date_to:
            domain.append((date_field, "<=", self.date_to))

        return domain

    def _compute_payment_domain(self):
        domain = [
            ("company_id", "=", self.env.company.id),
            ("state", "=", "posted"),
        ]

        date_field = "date" if "date" in self.env["account.payment"]._fields else "payment_date"

        if self.date_from:
            domain.append((date_field, ">=", self.date_from))

        if self.date_to:
            domain.append((date_field, "<=", self.date_to))

        return domain

    # -----------------------------
    # DATE VALIDATION
    # -----------------------------

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "warning": {
                    "title": _("Invalid date range"),
                    "message": _("Start date must be before end date."),
                }
            }

    # -----------------------------
    # PREFILL DATA
    # -----------------------------

    def action_prefill_by_date(self):
        self.ensure_one()

        invoices = self.env["account.move"].search(self._compute_invoice_domain())
        payments = self.env["account.payment"].search(self._compute_payment_domain())

        self.invoice_ids = invoices
        self.payment_ids = payments

        return {"type": "ir.actions.do_nothing"}

    # -----------------------------
    # SAFETY DEFAULTS
    # -----------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Prevent QWeb many2many crash
        res.setdefault("invoice_ids", [])
        res.setdefault("payment_ids", [])

        return res

    # -----------------------------
    # XML GENERATION
    # -----------------------------

    def action_generate_xml(self):
        self.ensure_one()

        if not self.configuration_id:
            raise UserError(_("Please select a Tally configuration."))

        invoices = self.invoice_ids
        payments = self.payment_ids

        # If nothing manually selected, use date filter
        if not invoices and not payments and (self.date_from or self.date_to):
            invoices = self.env["account.move"].search(self._compute_invoice_domain())
            payments = self.env["account.payment"].search(self._compute_payment_domain())

        if not invoices and not payments:
            raise UserError(
                _("Nothing to export. Please select invoices/payments or a date range.")
            )

        try:
            from ..services.xml_generator import TallyXMLGenerator
        except Exception:
            raise UserError(_("Tally XML generator service not found."))

        generator = TallyXMLGenerator(self.env)

        xml_content = generator.generate(
            configuration=self.configuration_id,
            invoices=invoices,
            payments=payments,
        )

        file_name = "tally_export_%s.xml" % fields.Date.today()

        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "type": "binary",
                "datas": base64.b64encode(xml_content.encode("utf-8")),
                "res_model": "tally.generate.xml",
                "res_id": self.id,
                "mimetype": "application/xml",
            }
        )

        _logger.info("Generated Tally XML attachment ID %s", attachment.id)

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }



# import base64
# import logging

# from odoo import api, fields, models, _
# from odoo.exceptions import UserError

# _logger = logging.getLogger(__name__)


# class TallyGenerateXML(models.TransientModel):
#     _name = "tally.generate.xml"
#     _description = "Generate Tally XML"
#     _rec_name = "configuration_id"

#     configuration_id = fields.Many2one(
#         "tally.configuration",
#         string="Configuration",
#         required=True,
#         domain=lambda self: [("company_id", "=", self.env.company.id)],
#     )

#     company_id = fields.Many2one(
#         "res.company",
#         string="Company",
#         related="configuration_id.company_id",
#         readonly=True,
#     )

#     date_from = fields.Date(string="Start Date")
#     date_to = fields.Date(string="End Date")

#     invoice_ids = fields.Many2many(
#         "account.move",
#         "tally_generate_invoice_rel",
#         "wizard_id",
#         "move_id",
#         string="Invoices / Bills",
#         domain=[
#             ("move_type", "in", ("out_invoice", "in_invoice", "out_refund", "in_refund")),
#             ("state", "=", "posted"),
#         ],
#         # Always return a valid (possibly empty) recordset for QWeb widgets
#         default=lambda self: self.env["account.move"],
#     )

#     payment_ids = fields.Many2many(
#         "account.payment",
#         "tally_generate_payment_rel",
#         "wizard_id",
#         "payment_id",
#         string="Payments",
#         domain=[("state", "=", "posted")],
#         # Always return a valid (possibly empty) recordset for QWeb widgets
#         default=lambda self: self.env["account.payment"],
#     )

#     export_customer_invoices = fields.Boolean(default=True)
#     export_vendor_bills = fields.Boolean(default=True)
#     export_credit_notes = fields.Boolean(default=True)
#     export_debit_notes = fields.Boolean(default=True)
#     export_customer_payments = fields.Boolean(default=True)
#     export_vendor_payments = fields.Boolean(default=True)

#     def _compute_domain_by_date(self):
#         """Helper for default domains by date range, used programmatically."""
#         domain = [("company_id", "=", self.env.company.id), ("state", "=", "posted")]
#         if self.date_from:
#             domain.append(("invoice_date", ">=", self.date_from))
#         if self.date_to:
#             domain.append(("invoice_date", "<=", self.date_to))
#         return domain

#     @api.onchange("date_from", "date_to")
#     def _onchange_dates(self):
#         if self.date_from and self.date_to and self.date_from > self.date_to:
#             return {
#                 "warning": {
#                     "title": _("Invalid date range"),
#                     "message": _("Start date must be before end date."),
#                 }
#             }

#     def action_prefill_by_date(self):
#         """Optional helper button (not exposed in view by default)."""
#         self.ensure_one()
#         move_domain = self._compute_domain_by_date()
#         self.invoice_ids = self.env["account.move"].search(move_domain)
#         return {"type": "ir.actions.do_nothing"}

#     @api.model
#     def default_get(self, fields_list):
#         """Ensure Many2many fields are never None for QWeb widgets."""
#         res = super().default_get(fields_list)
#         # QWeb many2many_checkboxes / many2many_tags expect an iterable
#         res.setdefault("invoice_ids", [])
#         res.setdefault("payment_ids", [])
#         return res

#     def action_generate_xml(self):
#         self.ensure_one()

#         if not self.configuration_id:
#             raise UserError(_("Please select a Tally configuration."))

#         invoices = self.invoice_ids
#         payments = self.payment_ids

#         if not invoices and not payments and (self.date_from or self.date_to):
#             move_domain = self._compute_domain_by_date()
#             invoices = self.env["account.move"].search(move_domain)

#         if not invoices and not payments:
#             raise UserError(_("Nothing to export. Please select invoices/payments or a date range."))

#         from ..services.xml_generator import TallyXMLGenerator

#         generator = TallyXMLGenerator(self.env)
#         xml_content = generator.generate(
#             configuration=self.configuration_id,
#             invoices=invoices,
#             payments=payments,
#         )

#         file_name = "tally_export_%s.xml" % fields.Date.today()
#         attachment = self.env["ir.attachment"].create(
#             {
#                 "name": file_name,
#                 "type": "binary",
#                 "datas": base64.b64encode(xml_content.encode("utf-8")),
#                 "res_model": "tally.generate.xml",
#                 "res_id": self.id,
#                 "mimetype": "application/xml",
#             }
#         )

#         _logger.info("Generated Tally XML attachment ID %s", attachment.id)

#         return {
#             "type": "ir.actions.act_url",
#             "url": "/web/content/%s?download=true" % attachment.id,
#             "target": "self",
#         }

