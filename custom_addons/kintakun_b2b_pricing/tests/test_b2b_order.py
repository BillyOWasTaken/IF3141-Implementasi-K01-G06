from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import B2BCommon


@tagged("post_install", "-at_install")
class TestB2BOrder(B2BCommon):
    def test_quotation_uses_agent_pricelist(self):
        order = self._new_order(self.agent_reguler)
        self.assertEqual(order.state, "draft")
        self.assertTrue(order.kintakun_is_b2b)
        self.assertEqual(order.pricelist_id, self.pricelist_reguler)
        self.assertEqual(order.kintakun_pricing_state, "applied")
        self.assertEqual(order.kintakun_tier_rule_id, self.rule_reguler)
        self.assertEqual(order.order_line.price_unit, 100000)
        self.assertEqual(order.order_line.discount, 5)
        self.assertEqual(order.kintakun_amount_gross, 1000000)
        self.assertEqual(order.kintakun_tier_discount_amount, 50000)
        self.assertEqual(order.amount_untaxed, 950000)

    def test_priority_agent_gets_seven_percent(self):
        order = self._new_order(self.agent_prioritas)
        self.assertEqual(order.pricelist_id, self.pricelist_prioritas)
        self.assertEqual(order.order_line.discount, 7)
        self.assertEqual(order.amount_untaxed, 930000)
        self.assertEqual(order.kintakun_priority, "1")

    def test_tier_plus_seasonal_promo(self):
        promo = self._promo()
        order = self._new_order(self.agent_reguler)
        self.assertEqual(order.kintakun_promo_rule_id, promo)
        self.assertEqual(order.order_line.discount, 8)
        self.assertEqual(order.kintakun_promo_discount_amount, 30000)
        self.assertEqual(order.amount_untaxed, 920000)

    def test_reprice_after_new_promo(self):
        order = self._new_order(self.agent_prioritas)
        self.assertEqual(order.order_line.discount, 7)
        self._promo(discount_percent=3)
        order.with_user(self.user_staf_sales).action_kintakun_reprice()
        self.assertEqual(order.order_line.discount, 10)
        self.assertEqual(order.amount_untaxed, 900000)

    def test_manual_price_change_ignored(self):
        order = self._new_order(self.agent_reguler)
        line = order.order_line.with_user(self.user_staf_sales)
        line.write({"discount": 50, "price_unit": 1})
        self.assertEqual(line.discount, 5)
        self.assertEqual(line.price_unit, 100000)
        forced = self.env["sale.order.line"].with_user(self.user_staf_sales).create(
            {
                "order_id": order.id,
                "product_id": self.product_other.id,
                "product_uom_qty": 1,
                "price_unit": 1,
                "discount": 99,
            }
        )
        self.assertEqual(forced.price_unit, 100000)
        self.assertEqual(forced.discount, 5)
        order.with_user(self.user_staf_sales).write({"pricelist_id": self.pricelist_prioritas.id})
        self.assertEqual(order.kintakun_pricing_state, "draft")
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self._new_order(self.agent_reguler, quantity=0)

    def test_confirm_blocked_without_approved_rule(self):
        self.rule_reguler.active = False
        order = self._new_order(self.agent_reguler)
        self.assertEqual(order.kintakun_pricing_state, "draft")
        self.assertEqual(order.order_line.discount, 0)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_region_quota_blocks_confirmation(self):
        self._promo(region_quota=15)
        first = self._new_order(self.agent_reguler, quantity=10)
        self.assertFalse(first.kintakun_quota_exceeded)
        first.action_confirm()
        second = self._new_order(self.agent_reguler, quantity=10)
        self.assertTrue(second.kintakun_quota_exceeded)
        self.assertIn("sisa kuota 5", second.kintakun_quota_message)
        with self.assertRaises(UserError):
            second.action_confirm()
        self.assertEqual(second.state, "draft")
        other_region = self._new_order(self.agent_prioritas, quantity=10)
        self.assertFalse(other_region.kintakun_quota_exceeded)

    def test_priority_star_and_queue(self):
        order_a = self._new_order(self.agent_reguler)
        order_b = self._new_order(self.agent_prioritas)
        order_a.action_confirm()
        order_b.action_confirm()
        self.assertLess(order_a.kintakun_queue_number, order_b.kintakun_queue_number)
        picking_a = order_a.sudo().picking_ids
        picking_b = order_b.sudo().picking_ids
        self.assertEqual(picking_a.state, "assigned")
        self.assertEqual(picking_b.state, "assigned")
        self.assertEqual(picking_b.priority, "1")
        self.assertEqual(picking_a.priority, "0")
        queue = self.env["stock.picking"].search([("id", "in", (picking_a | picking_b).ids)])
        self.assertEqual(queue[0], picking_b)
        self.assertEqual(self.product.qty_available, 50)
        self.assertEqual(self.product.virtual_available, 30)

        order_c = self._new_order(self.agent_reguler, quantity=60)
        order_c.action_confirm()
        self.assertEqual(order_c.state, "sale")
        self.assertEqual(order_c.sudo().picking_ids.state, "confirmed")

    def test_pricing_frozen_after_confirmation(self):
        order = self._new_order(self.agent_reguler)
        order.action_confirm()
        self.agent_reguler.agent_tier = "prioritas"
        self.env.flush_all()
        self.assertEqual(order.kintakun_agent_tier, "reguler")
        self.assertEqual(order.order_line.discount, 5)
        self.assertEqual(order.pricelist_id, self.pricelist_reguler)

    def test_non_agent_order_untouched(self):
        customer = self.env["res.partner"].create({"name": "Pembeli Eceran"})
        order = self._new_order(customer)
        self.assertFalse(order.kintakun_is_b2b)
        self.assertEqual(order.order_line.discount, 0)
