# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderTypology(models.Model):
    _name = "sale.order.type"
    _description = "Type of sale order"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Entry Sequence",
        copy=False,
        domain=lambda self: self._get_domain_sequence_id(),
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Billing Journal",
        domain="[('type', '=', 'sale'), '|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]",
        check_company=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse", string="Warehouse", check_company=True
    )
    picking_policy = fields.Selection(
        selection=lambda self: self._get_selection_picking_policy(),
        string="Shipping Policy",
        default=lambda self: self.env["sale.order"]
        .default_get(["picking_policy"])
        .get("picking_policy"),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        store=True,
    )
    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term", string="Payment Term", check_company=True
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist", string="Pricelist", check_company=True
    )
    incoterm_id = fields.Many2one(comodel_name="account.incoterms", string="Incoterm")
    route_id = fields.Many2one(
        "stock.route",
        string="Route",
        domain=[("sale_selectable", "=", True)],
        ondelete="restrict",
        check_company=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic account",
        check_company=True,
    )
    active = fields.Boolean(default=True)
    quotation_validity_days = fields.Integer(string="Quotation Validity (Days)")
    precedence = fields.Selection(
        [
            ("type_first", "Sale type wins"),
            ("partner_first", "Partner wins; type fills gaps"),
            ("partner_only", "Ignore type for propagation"),
        ],
        required=True,
        default=lambda self: (
            self.env.company.sale_order_type_default_precedence or "type_first"
        ),
        help="How this type resolves conflicts between its own pricelist / "
        "payment_term / warehouse / etc. and the partner's defaults when a "
        "sale order is created.\n"
        "- Sale type wins: legacy behavior. The type's value overrides the "
        "partner's whenever both are set.\n"
        "- Partner wins; type fills gaps: the partner's default is used; the "
        "type only fills fields the partner leaves empty.\n"
        "- Ignore type for propagation: fields on this type are not pushed "
        "onto sale orders at all; the type is then a labeling / reporting "
        "construct only.",
    )

    @api.model
    def _get_domain_sequence_id(self):
        seq_type = self.env.ref("sale.seq_sale_order")
        return [("code", "=", seq_type.code)]

    @api.model
    def _get_selection_picking_policy(self):
        return self.env["sale.order"].fields_get(allfields=["picking_policy"])[
            "picking_policy"
        ]["selection"]
