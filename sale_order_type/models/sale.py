# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2023 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Type",
        compute="_compute_sale_type_id",
        precompute=True,
        store=True,
        readonly=False,
        ondelete="restrict",
        copy=True,
        check_company=True,
    )
    order_type_required = fields.Boolean(related="company_id.sale_order_type_required")
    type_precedence = fields.Selection(
        related="type_id.precedence",
        help="The active precedence mode of this order's type — exposed for "
        "view-level hints, not user-editable here.",
    )
    # Fields converted to computed writable
    picking_policy = fields.Selection(
        compute="_compute_picking_policy", store=True, readonly=False
    )
    incoterm = fields.Many2one(compute="_compute_incoterm", store=True, readonly=False)

    @api.model
    def _default_type_id(self):
        return self.env["sale.order.type"].search(
            [("company_id", "in", [self.env.company.id, False])], limit=1
        )

    @api.model
    def _default_sequence_id(self):
        """We get the sequence in same way the core next_by_code method does so we can
        get the proper default sequence"""
        force_company = self.env.company.id
        return self.env["ir.sequence"].search(
            [
                ("code", "=", "sale.order"),
                "|",
                ("company_id", "=", force_company),
                ("company_id", "=", False),
            ],
            order="company_id",
            limit=1,
        )

    def _sot_resolve(self, type_value, current_value, fname=None):
        """Apply the active precedence mode of this order's `type_id`.

        Returns the value that the caller (a `_compute_*` body) should write
        to the order's field. `current_value` is whatever `super()` already
        set (usually the partner-derived default).

        `fname` (optional) — the name of the field being resolved. When the
        `web_field_provenance` module (Huly OCA-23) is installed and the
        user has manually edited this field on the order, the manual value
        is preserved regardless of precedence mode. This integration is a
        soft dependency: `_user_set` is only consulted if `record._user_set`
        exists, so installs without the provenance module behave exactly
        as before.
        """
        if fname and hasattr(self, "_user_set"):
            try:
                if self._user_set(fname):
                    return current_value
            except Exception as exc:
                # Provenance lookup must never break the compute; fall
                # through to the regular precedence resolution.
                _logger.debug("_user_set lookup failed for %s: %s", fname, exc)
        mode = self.type_id.precedence or "type_first"
        if mode == "partner_only":
            return current_value
        if mode == "partner_first":
            return current_value or type_value
        # type_first (legacy)
        return type_value or current_value

    def _sot_stamp_cascade_if_available(self, fname, value, type_value):
        """Stamp `fname` as rule-derived when the resolved value came from
        the type (not the partner default).

        Soft-dependency on the `web_field_provenance` module (Huly OCA-23):
        if `_stamp_provenance` is present on the record, attribute the
        cascade write so the OWL badge shows the green-cog icon and the
        tooltip reads "Set by Sale Order Type cascade". When the module
        isn't installed this is a silent no-op.
        """
        if not value or value != type_value:
            return
        if not hasattr(self, "_stamp_provenance"):
            return
        try:
            self._stamp_provenance(
                [fname],
                source="r",
                by="sot.cascade",
                rule="Sale Order Type cascade",
            )
        except Exception as exc:
            # Provenance stamping must never break the compute.
            _logger.debug("_stamp_provenance failed for %s: %s", fname, exc)

    @api.depends("partner_id", "company_id")
    @api.depends_context("partner_id", "company_id", "company")
    def _compute_sale_type_id(self):
        for record in self:
            # Specific partner sale type value
            sale_type = (
                record.partner_id.with_company(record.company_id).sale_type
                or record.partner_id.commercial_partner_id.with_company(
                    record.company_id
                ).sale_type
            )
            # Default user sale type value
            if not sale_type:
                sale_type = record.default_get(["type_id"]).get("type_id", False)
            # Get first sale type value
            if not sale_type:
                sale_type = record._default_type_id()
            record.type_id = sale_type

    @api.depends("type_id")
    def _compute_warehouse_id(self):
        res = super()._compute_warehouse_id()
        for order in self.filtered("type_id"):
            type_value = order.type_id.warehouse_id
            order.warehouse_id = order._sot_resolve(
                type_value, order.warehouse_id, "warehouse_id"
            )
            order._sot_stamp_cascade_if_available(
                "warehouse_id", order.warehouse_id, type_value
            )
        return res

    def _depends_picking_policy(self):
        depends = []
        if hasattr(super(), "_depends_picking_policy"):
            depends = super()._depends_picking_policy()
        depends.append("type_id")
        return depends

    @api.depends(lambda self: self._depends_picking_policy())
    def _compute_picking_policy(self):
        res = None
        if hasattr(super(), "_compute_picking_policy"):
            res = super()._compute_picking_policy()
        for order in self.filtered("type_id"):
            type_value = order.type_id.picking_policy
            order.picking_policy = order._sot_resolve(
                type_value, order.picking_policy, "picking_policy"
            )
            order._sot_stamp_cascade_if_available(
                "picking_policy", order.picking_policy, type_value
            )
        return res

    @api.depends("type_id")
    def _compute_payment_term_id(self):
        res = super()._compute_payment_term_id()
        for order in self.filtered("type_id"):
            type_value = order.type_id.payment_term_id
            order.payment_term_id = order._sot_resolve(
                type_value, order.payment_term_id, "payment_term_id"
            )
            order._sot_stamp_cascade_if_available(
                "payment_term_id", order.payment_term_id, type_value
            )
        return res

    @api.depends("type_id")
    def _compute_pricelist_id(self):
        res = super()._compute_pricelist_id()
        for order in self.filtered("type_id"):
            type_value = order.type_id.pricelist_id
            order.pricelist_id = order._sot_resolve(
                type_value, order.pricelist_id, "pricelist_id"
            )
            order._sot_stamp_cascade_if_available(
                "pricelist_id", order.pricelist_id, type_value
            )
        return res

    @api.depends("type_id")
    def _compute_incoterm(self):
        res = None
        if hasattr(super(), "_compute_incoterm"):
            res = super()._compute_incoterm()
        for order in self.filtered("type_id"):
            type_value = order.type_id.incoterm_id
            order.incoterm = order._sot_resolve(type_value, order.incoterm, "incoterm")
            order._sot_stamp_cascade_if_available(
                "incoterm", order.incoterm, type_value
            )
        return res

    @api.depends("type_id")
    def _compute_validity_date(self):
        res = super()._compute_validity_date()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.quotation_validity_days:
                order.validity_date = fields.Date.to_string(
                    datetime.now() + timedelta(order_type.quotation_validity_days)
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New") and vals.get("type_id"):
                sale_type = self.env["sale.order.type"].browse(vals["type_id"])
                if sale_type.sequence_id:
                    vals["name"] = sale_type.sequence_id.next_by_id(
                        sequence_date=vals.get("date_order")
                    )
        return super().create(vals_list)

    def write(self, vals):
        """A sale type could have a different order sequence, so we could
        need to change it accordingly"""
        if vals.get("type_id"):
            sale_type = self.env["sale.order.type"].browse(vals["type_id"])
            if sale_type.sequence_id:
                for record in self:
                    # An order with a type without sequence would get the default one.
                    # We want to avoid changing the order reference when the new
                    # sequence has the same default sequence.
                    ignore_default_sequence = (
                        not record.type_id.sequence_id
                        and sale_type.sequence_id
                        == record.with_company(record.company_id)._default_sequence_id()
                    )
                    if (
                        record.state in {"draft", "sent"}
                        and record.type_id.sequence_id != sale_type.sequence_id
                        and not ignore_default_sequence
                    ):
                        new_vals = vals.copy()
                        new_vals["name"] = sale_type.sequence_id.next_by_id(
                            sequence_date=vals.get("date_order")
                        )
                        super().write(new_vals)
                    else:
                        super().write(vals)
                return True
        return super().write(vals)

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        # Journal:
        # - `type_first`: legacy — type's journal overrides super's choice.
        # - `partner_first` / `partner_only`: leave whatever super chose.
        # We don't use `_sot_resolve` here: super() may leave `journal_id`
        # implicit (the account.move._get_default_journal logic fills it),
        # so a three-way merge would spuriously fall back to the type's
        # journal in non-type_first modes.
        mode = self.type_id.precedence or "type_first"
        if mode == "type_first" and self.type_id.journal_id:
            res["journal_id"] = self.type_id.journal_id.id
        if self.type_id:
            res["sale_type_id"] = self.type_id.id
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    route_id = fields.Many2one(compute="_compute_route_id", store=True, readonly=False)

    def _sot_stamp_cascade_if_available(self, fname, value, type_value):
        """Mirror of `SaleOrder._sot_stamp_cascade_if_available` for line-
        level fields (route_id). Same soft-dependency on
        `web_field_provenance` (Huly OCA-23).
        """
        if not value or value != type_value:
            return
        if not hasattr(self, "_stamp_provenance"):
            return
        try:
            self._stamp_provenance(
                [fname],
                source="r",
                by="sot.cascade",
                rule="Sale Order Type cascade",
            )
        except Exception as exc:
            _logger.debug("_stamp_provenance failed for %s: %s", fname, exc)

    @api.depends("order_id.type_id")
    def _compute_route_id(self):
        res = None
        if hasattr(super(), "_compute_route_id"):
            res = super()._compute_route_id()
        for line in self.filtered("order_id.type_id"):
            type_value = line.order_id.type_id.route_id
            line.route_id = line.order_id._sot_resolve(
                type_value, line.route_id, "route_id"
            )
            line._sot_stamp_cascade_if_available("route_id", line.route_id, type_value)
        return res
