# Copyright 2015 Oihane Crucelaegui - AvanzOSC
# Copyright 2017 Pierre Faniel - Niboo SPRL (<https://www.niboo.be/>)
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from freezegun import freeze_time

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import BaseCommon


class TestSaleOrderType(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_type_model = cls.env["sale.order.type"]
        cls.sale_order_model = cls.env["sale.order"]
        cls.invoice_model = cls.env["account.move"].with_context(
            default_move_type="out_invoice"
        )
        cls.account_model = cls.env["account.account"]
        cls.account = cls.account_model.create(
            {"code": "income", "name": "Income", "account_type": "income"}
        )
        cls.partner = cls.env.ref("base.res_partner_1")
        cls.partner_child_1 = cls.env["res.partner"].create(
            {"name": "Test child", "parent_id": cls.partner.id, "sale_type": False}
        )
        cls.sequence = cls.env["ir.sequence"].create(
            {
                "name": "Test Sales Order",
                "code": "sale.order",
                "prefix": "TSO",
                "padding": 3,
            }
        )
        cls.sequence_quot = cls.env["ir.sequence"].create(
            {
                "name": "Test Quotation Update",
                "code": "sale.order",
                "prefix": "TQU",
                "padding": 3,
            }
        )
        # Ensure that get sale journal has the same company that environment
        cls.journal = cls.env["account.journal"].search(
            [
                ("company_id", "=", cls.env.company.id),
                ("type", "=", "sale"),
            ],
            limit=1,
        )
        cls.default_sale_type_id = cls.env["sale.order.type"].search([], limit=1)
        cls.default_sale_type_id.sequence_id = False
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Warehouse Test", "code": "WT"}
        )
        cls.product = cls.env["product.product"].create(
            {"type": "service", "invoice_policy": "order", "name": "Test product"}
        )
        cls.immediate_payment = cls.env.ref("account.account_payment_term_immediate")
        cls.sale_pricelist = cls.env["product.pricelist"].create(
            {"name": "Public Pricelist", "sequence": 1}
        )
        cls.free_carrier = cls.env.ref("account.incoterm_FCA")
        cls.sale_type = cls.sale_type_model.create(
            {
                "name": "Test Sale Order Type",
                "sequence_id": cls.sequence.id,
                "journal_id": cls.journal.id,
                "warehouse_id": cls.warehouse.id,
                "picking_policy": "one",
                "payment_term_id": cls.immediate_payment.id,
                "pricelist_id": cls.sale_pricelist.id,
                "incoterm_id": cls.free_carrier.id,
                "quotation_validity_days": 10,
            }
        )
        cls.sale_type_quot = cls.sale_type_model.create(
            {
                "name": "Test Quotation Type",
                "sequence_id": cls.sequence_quot.id,
                "journal_id": cls.journal.id,
                "warehouse_id": cls.warehouse.id,
                "picking_policy": "one",
                "payment_term_id": cls.immediate_payment.id,
                "pricelist_id": cls.sale_pricelist.id,
                "incoterm_id": cls.free_carrier.id,
            }
        )
        cls.sale_type_sequence_default = cls.sale_type_quot.copy(
            {
                "name": "Test Sequence default",
                "sequence_id": cls.env["sale.order"]
                .with_company(cls.env.company.id)
                ._default_sequence_id()
                .id,
            }
        )
        cls.partner.sale_type = cls.sale_type
        cls.sale_route = cls.env["stock.route"].create(
            {
                "name": "SO -> Customer",
                "product_selectable": True,
                "sale_selectable": True,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "SO -> Customer",
                            "action": "pull",
                            "picking_type_id": cls.env.ref("stock.picking_type_in").id,
                            "location_src_id": cls.env.ref(
                                "stock.stock_location_components"
                            ).id,
                            "location_dest_id": cls.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        cls.sale_type_route = cls.sale_type_model.create(
            {
                "name": "Test Sale Order Type-1",
                "sequence_id": cls.sequence.id,
                "journal_id": cls.journal.id,
                "warehouse_id": cls.warehouse.id,
                "picking_policy": "one",
                "payment_term_id": cls.immediate_payment.id,
                "pricelist_id": cls.sale_pricelist.id,
                "incoterm_id": cls.free_carrier.id,
                "route_id": cls.sale_route.id,
            }
        )

    def create_sale_order(self, partner=False):
        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = partner or self.partner
        with sale_form.order_line.new() as order_line:
            order_line.product_id = self.product
            order_line.product_uom_qty = 1.0
        return sale_form.save()

    def create_invoice(self, partner=False, sale_type=False):
        inv_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        inv_form.partner_id = partner or self.partner
        inv_form.sale_type_id = sale_type or self.sale_type
        with inv_form.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.product
            inv_line.account_id = self.account
            inv_line.quantity = 1.0
        return inv_form.save()

    def test_sale_order_flow(self):
        sale_type = self.sale_type
        order = self.create_sale_order()
        self.assertEqual(order.type_id, sale_type)
        self.assertEqual(order.warehouse_id, sale_type.warehouse_id)
        self.assertEqual(order.picking_policy, sale_type.picking_policy)
        self.assertEqual(order.payment_term_id, sale_type.payment_term_id)
        self.assertEqual(order.pricelist_id, sale_type.pricelist_id)
        self.assertEqual(order.incoterm, sale_type.incoterm_id)
        order.action_confirm()
        invoice = order._create_invoices()
        self.assertEqual(invoice.sale_type_id, sale_type)
        self.assertEqual(invoice.journal_id, sale_type.journal_id)

    def test_sale_order_change_partner(self):
        order = self.create_sale_order()
        self.assertEqual(order.type_id, self.sale_type)
        order = self.create_sale_order(partner=self.partner_child_1)
        self.assertEqual(order.type_id, self.sale_type)

    def test_sale_order_without_partner(self):
        sale_order = self.sale_order_model.with_company(1).new()
        self.assertEqual(sale_order.company_id.id, 1)
        sale_type = self.env["sale.order.type"].search(
            [("company_id", "in", [sale_order.company_id.id, False])], limit=1
        )
        self.assertEqual(sale_order.type_id, sale_type)

    def test_invoice_onchange_type(self):
        sale_type = self.sale_type
        invoice = self.create_invoice()
        self.assertEqual(invoice.invoice_payment_term_id, sale_type.payment_term_id)
        self.assertEqual(invoice.journal_id, sale_type.journal_id)

    def test_invoice_change_partner(self):
        invoice = self.create_invoice()
        self.assertEqual(invoice.sale_type_id, self.sale_type)
        invoice = self.create_invoice(partner=self.partner_child_1)
        self.assertEqual(invoice.sale_type_id, self.sale_type)

    def test_invoice_without_partner(self):
        invoice = self.invoice_model.new()
        self.assertEqual(invoice.sale_type_id, self.default_sale_type_id)

    def test_sale_order_flow_route(self):
        order = self.create_sale_order()
        order.type_id = self.sale_type_route.id
        self.assertEqual(order.type_id.route_id, order.order_line[0].route_id)
        sale_line_dict = {
            "product_id": self.product.id,
            "name": self.product.name,
            "product_uom_qty": 2.0,
            "price_unit": self.product.lst_price,
        }
        order.write({"order_line": [(0, 0, sale_line_dict)]})
        self.assertEqual(order.type_id.route_id, order.order_line[1].route_id)

    def test_sale_order_in_draft_state_update_name(self):
        order = self.create_sale_order()
        self.assertEqual(order.type_id, self.sale_type)
        self.assertEqual(order.state, "draft")
        self.assertTrue(order.name.startswith("TSO"))
        # change order type on sale order
        order.type_id = self.sale_type_quot
        self.assertEqual(order.type_id, self.sale_type_quot)
        self.assertTrue(order.name.startswith("TQU"))

    def test_sale_order_in_sent_state_update_name(self):
        order = self.create_sale_order()
        self.assertEqual(order.type_id, self.sale_type)
        self.assertEqual(order.state, "draft")
        self.assertTrue(order.name.startswith("TSO"))
        # send quotation
        order.action_quotation_sent()
        self.assertTrue(order.state == "sent", "Sale: state after sending is wrong")
        order.type_id = self.sale_type_quot
        self.assertEqual(order.type_id, self.sale_type_quot)
        self.assertTrue(order.name.startswith("TQU"))

    @freeze_time("2022-01-01")
    def test_sale_order_quotation_validity(self):
        order = self.create_sale_order()
        self.assertEqual(fields.Date.to_string(order.validity_date), "2022-01-11")

    def test_sale_order_create_invoice_down_payment(self):
        order = self.create_sale_order()
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(
                active_model="sale.order", active_id=order.id, active_ids=order.ids
            )
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 10,
                }
            )
        )
        wizard.create_invoices()
        self.assertEqual(order.type_id.journal_id, order.invoice_ids[0].journal_id)
        self.assertEqual(order.type_id, order.invoice_ids[0].sale_type_id)

    def test_sequence_default(self):
        """When the previous type had no sequence the order gets the default one. The
        sequence change shouldn't be triggered, otherwise we'd get a different number
        from the same sequence"""
        self.partner.sale_type = self.default_sale_type_id
        order = self.create_sale_order()
        name = order.name
        order.type_id = self.sale_type_sequence_default
        self.assertEqual(name, order.name, "The sequence shouldn't change!")

    def test_res_partner_copy_data(self):
        new_partner = self.partner.copy()
        self.assertEqual(self.partner.sale_type, new_partner.sale_type)

    def test_effective_pricelist_id_with_pricelist(self):
        """effective_pricelist_id resolves to sale_type.pricelist_id when set."""
        self.partner.sale_type = self.sale_type
        self.assertEqual(
            self.partner.effective_pricelist_id, self.sale_type.pricelist_id
        )

    def test_effective_pricelist_id_without_pricelist(self):
        """effective_pricelist_id is empty when sale_type has no pricelist set."""
        sale_type_no_pricelist = self.sale_type_model.create(
            {"name": "Type without pricelist"}
        )
        self.partner.sale_type = sale_type_no_pricelist
        self.assertFalse(self.partner.effective_pricelist_id)

    def test_effective_pricelist_id_without_sale_type(self):
        """effective_pricelist_id is empty when the partner has no sale_type."""
        self.partner.sale_type = False
        self.assertFalse(self.partner.effective_pricelist_id)

    def test_sale_order_type_required(self):
        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = self.partner
        with sale_form.order_line.new() as order_line:
            order_line.product_id = self.product
            order_line.product_uom_qty = 1.0
        sale_form.type_id = self.sale_type.browse()
        with self.assertRaises(AssertionError):
            sale_form.save()

    def test_sale_order_type_not_required(self):
        self.env.company.sale_order_type_required = False
        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = self.partner
        with sale_form.order_line.new() as order_line:
            order_line.product_id = self.product
            order_line.product_uom_qty = 1.0
        sale_form.type_id = self.sale_type.browse()
        sale_form.save()

    def test_credit_note_preserves_sale_type_from_sale_order(self):
        """Test credit notes preserve sale order type.

        When creating a credit note (refund) from an invoice that originated
        from a sale order, the sale_type_id from the sale order should be
        maintained and not overridden by the partner's default sale type.
        """
        # Create a test partner with a specific default sale type
        test_partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "sale_type": self.sale_type_quot.id,
            }
        )
        # Create and confirm a sale order with a DIFFERENT sale type
        # than partner's default
        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = test_partner
        sale_form.type_id = self.sale_type
        with sale_form.order_line.new() as order_line:
            order_line.product_id = self.product
        sale_order = sale_form.save()
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        # Create a credit note (refund) from the invoice
        refund_wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "reason": "Test refund",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        refund_action = refund_wizard.refund_moves()
        credit_note = self.env["account.move"].browse(refund_action["res_id"])
        # CRITICAL ASSERTION: Credit note should preserve the sale order's type,
        # NOT default to the partner's sale type
        self.assertEqual(
            credit_note._origin.sale_type_id,
            sale_order.type_id,
            "Credit note should preserve sale type from sale order "
            f"(expected: {sale_order.type_id.name}), "
            "not use partner's default sale type "
            f"(partner has: {sale_order.partner_id.sale_type.name})",
        )


@tagged("post_install", "-at_install")
class TestPrecedence(BaseCommon):
    """Cover the three precedence modes on `sale.order.type`.

    Strategy: unit-test the resolver helper directly with synthetic
    inputs, then a handful of full-flow integration tests for the
    cases we can drive without fighting Odoo's per-company property
    field plumbing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Precedence Test Partner",
                "is_company": True,
                "country_id": cls.env.ref("base.us").id,
            }
        )
        cls.pl_partner = cls.env["product.pricelist"].create(
            {"name": "Partner Pricelist", "company_id": False}
        )
        cls.pl_type = cls.env["product.pricelist"].create(
            {"name": "Type Pricelist", "company_id": False}
        )
        cls.pt_type = cls.env["account.payment.term"].create(
            {"name": "Type Payment Term"}
        )
        cls.wh_type = cls.env["stock.warehouse"].create(
            {"name": "Type Warehouse", "code": "TYP"}
        )
        cls.inc_type = cls.env.ref("account.incoterm_EXW")
        cls.route_type = cls.env["stock.route"].create(
            {"name": "Type Route", "sale_selectable": True}
        )
        cls.journal_type = cls.env["account.journal"].create(
            {"name": "Type Journal", "type": "sale", "code": "TYPJ"}
        )

        cls.type_full = cls.env["sale.order.type"].create(
            {
                "name": "Full Type",
                "pricelist_id": cls.pl_type.id,
                "payment_term_id": cls.pt_type.id,
                "warehouse_id": cls.wh_type.id,
                "picking_policy": "one",
                "incoterm_id": cls.inc_type.id,
                "route_id": cls.route_type.id,
                "journal_id": cls.journal_type.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"type": "service", "invoice_policy": "order", "name": "P"}
        )

    def _set_mode(self, mode):
        self.type_full.precedence = mode

    def _new_so(self):
        f = Form(self.env["sale.order"])
        f.partner_id = self.partner
        f.type_id = self.type_full
        with f.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 1.0
        return f.save()

    # ----- _sot_resolve helper (unit) ----------------------------------

    def test_sot_resolve_type_first_picks_type(self):
        self._set_mode("type_first")
        order = self.env["sale.order"].new({"type_id": self.type_full.id})
        self.assertEqual(order._sot_resolve("type-val", "current-val"), "type-val")

    def test_sot_resolve_type_first_falls_back_to_current(self):
        """type_first: when type is empty, keep super's value."""
        self._set_mode("type_first")
        order = self.env["sale.order"].new({"type_id": self.type_full.id})
        self.assertEqual(order._sot_resolve(False, "current-val"), "current-val")

    def test_sot_resolve_partner_first_picks_current(self):
        self._set_mode("partner_first")
        order = self.env["sale.order"].new({"type_id": self.type_full.id})
        self.assertEqual(order._sot_resolve("type-val", "current-val"), "current-val")

    def test_sot_resolve_partner_first_fills_gap_with_type(self):
        self._set_mode("partner_first")
        order = self.env["sale.order"].new({"type_id": self.type_full.id})
        self.assertEqual(order._sot_resolve("type-val", False), "type-val")

    def test_sot_resolve_partner_only_ignores_type(self):
        self._set_mode("partner_only")
        order = self.env["sale.order"].new({"type_id": self.type_full.id})
        self.assertEqual(order._sot_resolve("type-val", "current-val"), "current-val")

    def test_sot_resolve_partner_only_leaves_empty(self):
        self._set_mode("partner_only")
        order = self.env["sale.order"].new({"type_id": self.type_full.id})
        self.assertFalse(order._sot_resolve("type-val", False))

    # ----- integration: type_first end-to-end ---------------------------

    def test_type_first_pricelist(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order.pricelist_id, self.pl_type)

    def test_type_first_payment_term(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order.payment_term_id, self.pt_type)

    def test_type_first_warehouse(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order.warehouse_id, self.wh_type)

    def test_type_first_picking_policy(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order.picking_policy, "one")

    def test_type_first_incoterm(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order.incoterm, self.inc_type)

    def test_type_first_route(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order.order_line.route_id, self.route_type)

    def test_type_first_invoice_journal(self):
        self._set_mode("type_first")
        order = self._new_so()
        self.assertEqual(order._prepare_invoice()["journal_id"], self.journal_type.id)

    # ----- integration: partner_only end-to-end -------------------------
    # (No need for partner.property_product_pricelist setup — the test
    # asserts that the type's value is NOT propagated regardless of
    # partner state.)

    def test_partner_only_no_invoice_journal_override(self):
        self._set_mode("partner_only")
        order = self._new_so()
        self.assertNotEqual(
            order._prepare_invoice().get("journal_id"), self.journal_type.id
        )

    def test_partner_only_warehouse_not_propagated(self):
        self._set_mode("partner_only")
        order = self._new_so()
        # Whatever warehouse super() chose, it should not be the type's.
        self.assertNotEqual(order.warehouse_id, self.wh_type)

    def test_partner_only_picking_policy_not_propagated(self):
        self._set_mode("partner_only")
        order = self._new_so()
        # Default picking_policy is 'direct'; type carries 'one'.
        self.assertEqual(order.picking_policy, "direct")

    def test_partner_only_incoterm_not_propagated(self):
        self._set_mode("partner_only")
        order = self._new_so()
        self.assertFalse(order.incoterm)

    def test_partner_only_route_not_propagated(self):
        self._set_mode("partner_only")
        order = self._new_so()
        self.assertFalse(order.order_line.route_id)

    # ----- cross-cutting ------------------------------------------------

    def test_per_type_precedence_independent(self):
        """Two types with different precedence yield different SO results.
        Asserts on warehouse_id which is reliably propagated without
        needing partner-property setup.
        """
        other_type = self.type_full.copy(
            {"name": "Partner-only Twin", "precedence": "partner_only"}
        )
        self.type_full.precedence = "type_first"

        f1 = Form(self.env["sale.order"])
        f1.partner_id = self.partner
        f1.type_id = self.type_full
        with f1.order_line.new() as line:
            line.product_id = self.product
        so1 = f1.save()
        self.assertEqual(so1.warehouse_id, self.wh_type)

        f2 = Form(self.env["sale.order"])
        f2.partner_id = self.partner
        f2.type_id = other_type
        with f2.order_line.new() as line:
            line.product_id = self.product
        so2 = f2.save()
        self.assertNotEqual(so2.warehouse_id, self.wh_type)

    def test_new_type_inherits_company_default(self):
        self.env.company.sale_order_type_default_precedence = "partner_first"
        new_type = self.env["sale.order.type"].create({"name": "Inheritor"})
        self.assertEqual(new_type.precedence, "partner_first")
        # Reset for downstream tests.
        self.env.company.sale_order_type_default_precedence = "type_first"

    def test_existing_default_type_is_type_first(self):
        """The seed `default_type` ships with type_first to preserve behavior."""
        default_type = self.env.ref(
            "sale_order_type.default_type", raise_if_not_found=False
        )
        if default_type:
            self.assertEqual(default_type.precedence, "type_first")

    def test_manual_pricelist_edit_preserved_after_unrelated_write(self):
        self._set_mode("type_first")
        order = self._new_so()
        order.pricelist_id = self.pl_partner
        order.note = "Some unrelated edit"
        self.assertEqual(order.pricelist_id, self.pl_partner)

    def test_manual_pricelist_edit_overridden_on_type_change(self):
        self._set_mode("type_first")
        order = self._new_so()
        order.pricelist_id = self.pl_partner
        other_type = self.type_full.copy(
            {"name": "Trigger", "precedence": "type_first"}
        )
        order.type_id = other_type
        self.assertEqual(order.pricelist_id, self.pl_type)

    # ----- effective_* related fields on res.partner -------------------

    def test_effective_pricelist_id_related(self):
        self.partner.sale_type = self.type_full
        self.assertEqual(self.partner.effective_pricelist_id, self.pl_type)

    def test_effective_payment_term_id_related(self):
        self.partner.sale_type = self.type_full
        self.assertEqual(self.partner.effective_payment_term_id, self.pt_type)

    def test_effective_warehouse_id_related(self):
        self.partner.sale_type = self.type_full
        self.assertEqual(self.partner.effective_warehouse_id, self.wh_type)

    def test_effective_incoterm_id_related(self):
        self.partner.sale_type = self.type_full
        self.assertEqual(self.partner.effective_incoterm_id, self.inc_type)

    def test_effective_route_id_related(self):
        self.partner.sale_type = self.type_full
        self.assertEqual(self.partner.effective_route_id, self.route_type)

    def test_effective_journal_id_related(self):
        self.partner.sale_type = self.type_full
        self.assertEqual(self.partner.effective_journal_id, self.journal_type)

    def test_effective_precedence_related(self):
        self.partner.sale_type = self.type_full
        self.type_full.precedence = "partner_first"
        self.assertEqual(self.partner.effective_precedence, "partner_first")
