from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import B2BCommon
from odoo.addons.sale.models.sale_order import SaleOrder


@tagged("post_install", "-at_install")
class TestAccountingSync(B2BCommon):
    def _deliver(self, agent=None):
        order, picking = self._confirmed_picking(agent)
        self._pass_check(picking)
        picking.button_validate()
        return order.sudo(), picking

    def _logs(self, order, log_type):
        return order.kintakun_sync_log_ids.filtered(lambda log: log.log_type == log_type)

    def test_delivery_creates_draft_invoice(self):
        order, picking = self._deliver()
        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.kintakun_sale_id, order)
        self.assertEqual(invoice.partner_id, self.agent_prioritas)
        self.assertEqual(invoice.amount_total, order.amount_total)
        self.assertEqual(invoice.amount_untaxed, 930000)
        self.assertEqual(invoice.invoice_line_ids.quantity, 10)

        stock_log = self._logs(order, "stock")
        self.assertEqual(stock_log.state, "success")
        self.assertEqual(stock_log.picking_id, picking.sudo())
        invoice_log = self._logs(order, "invoice")
        self.assertEqual(invoice_log.state, "success")
        self.assertEqual(invoice_log.invoice_id, invoice)

    def test_invoice_posting_and_payment(self):
        order, _picking = self._deliver(self.agent_reguler)
        invoice = order.invoice_ids.with_user(self.user_manajer_finance)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(self.agent_reguler.kintakun_receivable, 950000)

        self.env["account.payment.register"].with_user(self.user_manajer_finance).with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({})._create_payments()
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        self.env.invalidate_all()
        self.assertEqual(self.agent_reguler.kintakun_receivable, 0)
        self.assertEqual(len(self._logs(order, "invoice")), 2)
        self.assertEqual(self._logs(order, "payment").state, "success")

    def test_failed_sync_is_logged_and_retried(self):
        def failing(self, *args, **kwargs):
            raise UserError("Modul keuangan tidak dapat dihubungi")

        with patch.object(SaleOrder, "_create_invoices", failing):
            order, picking = self._deliver()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self.product.qty_available, 40)
        self.assertFalse(order.invoice_ids)
        log = self._logs(order, "invoice")
        self.assertEqual(log.state, "failed")
        self.assertTrue(order.kintakun_sync_failed)

        log.with_user(self.user_manajer_finance).action_retry()
        self.assertEqual(log.state, "resolved")
        self.assertEqual(order.invoice_ids.state, "draft")

    def test_staf_inventory_cannot_touch_invoices(self):
        order, _picking = self._deliver()
        with self.assertRaises(AccessError):
            order.invoice_ids.with_user(self.user_staf_inventory).action_post()
