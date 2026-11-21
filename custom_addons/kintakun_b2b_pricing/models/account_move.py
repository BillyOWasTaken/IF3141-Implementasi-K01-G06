from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    kintakun_sale_id = fields.Many2one(
        "sale.order", string="Sales Order Agen", readonly=True, copy=False, index=True
    )
    kintakun_agent_tier = fields.Selection(
        related="kintakun_sale_id.kintakun_agent_tier", string="Tier Agen", store=True
    )

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted.filtered("kintakun_sale_id"):
            self.env["kintakun.sync.log"]._log(
                "invoice",
                "success",
                _(
                    "Faktur %(name)s disahkan; piutang agen bertambah %(amount)s.",
                    name=move.name,
                    amount=move.currency_id.format(move.amount_total),
                ),
                sale=move.kintakun_sale_id,
                invoice=move,
            )
        return posted

    def _invoice_paid_hook(self):
        res = super()._invoice_paid_hook()
        for move in self.filtered("kintakun_sale_id"):
            self.env["kintakun.sync.log"]._log(
                "payment",
                "success",
                _("Pembayaran faktur %s diterima; status faktur lunas.", move.name),
                sale=move.kintakun_sale_id,
                invoice=move,
            )
        return res
