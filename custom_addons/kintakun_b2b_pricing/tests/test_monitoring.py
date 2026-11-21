from odoo.tests import tagged

from .common import B2BCommon


@tagged("post_install", "-at_install")
class TestStockMonitor(B2BCommon):
    def _monitor(self, product):
        self.env.flush_all()
        self.env.invalidate_all()
        return self.env["kintakun.stock.monitor"].search([("product_id", "=", product.id)])

    def test_stock_and_open_demand(self):
        row = self._monitor(self.product)
        self.assertEqual(row.qty_on_hand, 50)
        self.assertEqual(row.qty_open_demand, 0)
        self.assertEqual(row.stock_status, "ok")

        _order, picking = self._confirmed_picking(quantity=10)
        row = self._monitor(self.product)
        self.assertEqual(row.qty_reserved, 10)
        self.assertEqual(row.qty_available, 40)
        self.assertEqual(row.qty_open_demand, 10)
        self.assertEqual(row.qty_shortage, 0)

        self._pass_check(picking)
        picking.button_validate()
        row = self._monitor(self.product)
        self.assertEqual(row.qty_on_hand, 40)
        self.assertEqual(row.qty_open_demand, 0)
        self.assertEqual(row.qty_delivered, 10)

    def test_procurement_need(self):
        self._confirmed_picking(agent=self.agent_reguler, quantity=60)
        row = self._monitor(self.product)
        self.assertEqual(row.qty_shortage, 10)
        self.assertEqual(row.stock_status, "short")
