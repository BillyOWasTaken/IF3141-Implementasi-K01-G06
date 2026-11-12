from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import KintakunCommon


@tagged("post_install", "-at_install")
class TestProcurement(KintakunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Vendor Uji Tekstil", "is_company": True, "supplier_rank": 1}
        )

    def _purchase_values(self, quantity=40):
        return {
            "partner_id": self.vendor.id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product.id,
                        "product_qty": quantity,
                        "price_unit": 60000,
                        "taxes_id": [(5, 0, 0)],
                    },
                )
            ],
        }

    def test_purchase_order_to_stock(self):
        order = (
            self.env["purchase.order"]
            .with_user(self.user_manajer_procurement)
            .create(self._purchase_values())
        )
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.amount_untaxed, 2400000)
        order.button_confirm()
        self.assertEqual(order.state, "purchase")

        receipt = order.picking_ids
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt.picking_type_code, "incoming")
        self.assertEqual(self.product.qty_available, 0)

        receipt = receipt.with_user(self.user_staf_inventory)
        receipt.move_ids.write({"quantity": 40, "picked": True})
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")
        self.assertEqual(self.product.qty_available, 40)
        self.assertEqual(order.order_line.qty_received, 40)

    def test_staf_sales_cannot_create_purchase_order(self):
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(self.user_staf_sales).create(
                self._purchase_values()
            )
