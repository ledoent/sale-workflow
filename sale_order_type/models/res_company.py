# Copyright 2025 ACSONE SA/NV (https://acsone.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_order_type_required = fields.Boolean(
        default=True, help="If checked, the sale orders will require a type."
    )
    sale_order_type_default_precedence = fields.Selection(
        [
            ("type_first", "Sale type wins"),
            ("partner_first", "Partner wins; type fills gaps"),
            ("partner_only", "Ignore type for propagation"),
        ],
        default="type_first",
        required=True,
        help="Default precedence applied to newly-created sale order types. "
        "The actual behavior is set per-type and visible only in developer mode "
        "on the sale.order.type form.",
    )
