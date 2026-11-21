from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import B2BCommon


@tagged("post_install", "-at_install")
class TestFulfillmentCheck(B2BCommon):
    def test_validate_blocked_before_check(self):
        _order, picking = self._confirmed_picking()
        self.assertEqual(picking.kintakun_check_state, "waiting")
        with self.assertRaises(UserError):
            picking.button_validate()
        self.assertEqual(picking.state, "assigned")

    def test_matching_goods_release_delivery(self):
        order, picking = self._confirmed_picking()
        self._pass_check(picking)
        self.assertEqual(picking.kintakun_check_state, "checked")
        self.assertEqual(picking.kintakun_checker_id, self.user_staf_inventory)
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.kintakun_check_state, "validated")
        self.assertEqual(self.product.qty_available, 40)
        self.assertEqual(order.sudo().order_line.qty_delivered, 10)

    def test_quantity_mismatch_holds_delivery(self):
        _order, picking = self._confirmed_picking()
        picking.action_kintakun_start_check()
        picking.kintakun_check_line_ids.write({"qty_checked": 8, "product_ok": True})
        picking.action_kintakun_finish_check()
        self.assertEqual(picking.kintakun_check_state, "failed")
        with self.assertRaises(UserError):
            picking.button_validate()
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(self.product.qty_available, 50)

        self._pass_check(picking)
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_wrong_motif_holds_delivery(self):
        _order, picking = self._confirmed_picking()
        picking.action_kintakun_start_check()
        picking.kintakun_check_line_ids.write({"qty_checked": 10, "product_ok": False})
        picking.action_kintakun_finish_check()
        self.assertEqual(picking.kintakun_check_state, "failed")

    def test_scan_rejects_product_outside_order(self):
        _order, picking = self._confirmed_picking()
        picking.action_kintakun_start_check()
        Scan = self.env["kintakun.fulfillment.scan"].with_user(self.user_staf_inventory)
        line = picking.kintakun_check_line_ids
        with self.assertRaises(UserError):
            Scan.create({"picking_id": picking.id, "barcode": "T-GEO-160"}).action_scan()
        self.assertEqual(line.qty_checked, 0)
        Scan.create({"picking_id": picking.id, "barcode": "T-BNG-160", "quantity": 10}).action_scan()
        self.assertEqual(line.qty_checked, 10)
        self.assertEqual(line.result, "match")
        with self.assertRaises(UserError):
            Scan.create({"picking_id": picking.id, "barcode": "T-BNG-160"}).action_scan()

    def test_quantity_tampering_after_check(self):
        _order, picking = self._confirmed_picking()
        self._pass_check(picking)
        picking.move_ids.quantity = 8
        with self.assertRaises(UserError):
            picking.button_validate()

    def test_check_requires_ready_state(self):
        _order, picking = self._confirmed_picking(quantity=60)
        with self.assertRaises(UserError):
            picking.action_kintakun_start_check()
