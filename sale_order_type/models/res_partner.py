# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_type = fields.Many2one(
        comodel_name="sale.order.type",
        string="Sale Order Type",
        company_dependent=True,
        copy=True,
    )

    effective_pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Sale Effective Pricelist",
        related="sale_type.pricelist_id",
    )
    effective_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Sale Effective Payment Term",
        related="sale_type.payment_term_id",
    )
    effective_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Sale Effective Warehouse",
        related="sale_type.warehouse_id",
    )
    effective_incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        string="Sale Effective Incoterm",
        related="sale_type.incoterm_id",
    )
    effective_route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Sale Effective Route",
        related="sale_type.route_id",
    )
    effective_picking_policy = fields.Selection(
        string="Sale Effective Shipping Policy",
        related="sale_type.picking_policy",
    )
    effective_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Sale Effective Billing Journal",
        related="sale_type.journal_id",
    )
    effective_precedence = fields.Selection(
        string="Sale Effective Precedence",
        related="sale_type.precedence",
    )

    def copy_data(self, default=None):
        result = super().copy_data(default=default)
        for idx, partner in enumerate(self):
            values = result[idx]
            if partner.sale_type and not values.get("sale_type"):
                values["sale_type"] = partner.sale_type
        return result
