from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KintakunSyncLog(models.Model):
    _name = "kintakun.sync.log"
    _description = "Log Sinkronisasi ERP"
    _order = "sync_date desc, id desc"

    name = fields.Char(string="Nomor Log", required=True, readonly=True, default="/")
    log_type = fields.Selection(
        [
            ("stock", "Pemotongan Stok"),
            ("invoice", "Faktur Piutang"),
            ("payment", "Pembayaran"),
        ],
        string="Jenis Log",
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        [("success", "Berhasil"), ("failed", "Gagal"), ("resolved", "Sudah Disinkron Ulang")],
        string="Status Sinkronisasi",
        required=True,
        readonly=True,
    )
    sync_date = fields.Datetime(
        string="Waktu Sinkronisasi", required=True, readonly=True, default=fields.Datetime.now
    )
    user_id = fields.Many2one(
        "res.users", string="Pengguna", readonly=True, default=lambda self: self.env.user
    )
    sale_id = fields.Many2one("sale.order", string="Sales Order", readonly=True, index=True)
    partner_id = fields.Many2one(related="sale_id.partner_id", string="Agen", store=True)
    picking_id = fields.Many2one("stock.picking", string="Surat Jalan", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Faktur", readonly=True)
    invoice_date = fields.Date(related="invoice_id.invoice_date", string="Tanggal Faktur")
    currency_id = fields.Many2one(related="invoice_id.currency_id")
    amount_total = fields.Monetary(related="invoice_id.amount_total", string="Total Tagihan")
    invoice_state = fields.Selection(related="invoice_id.state", string="Status Faktur")
    payment_state = fields.Selection(
        related="invoice_id.payment_state", string="Status Pembayaran"
    )
    message = fields.Text(string="Keterangan", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].sudo().next_by_code("kintakun.sync.log")
        return super().create(vals_list)

    @api.model
    def _log(self, log_type, state, message, sale=None, picking=None, invoice=None):
        return self.sudo().create(
            {
                "log_type": log_type,
                "state": state,
                "message": message,
                "user_id": self.env.user.id,
                "sale_id": sale.id if sale else False,
                "picking_id": picking.id if picking else False,
                "invoice_id": invoice.id if invoice else False,
            }
        )

    def action_retry(self):
        for log in self:
            if log.state != "failed" or log.log_type != "invoice":
                raise UserError(_("Hanya log faktur berstatus Gagal yang dapat disinkron ulang."))
            if log.sale_id._kintakun_sync_invoice(log.picking_id):
                log.sudo().state = "resolved"
        return True

    @api.model
    def _cron_retry_failed(self):
        failed = self.search([("state", "=", "failed"), ("log_type", "=", "invoice")])
        for log in failed:
            if log.sale_id._kintakun_sync_invoice(log.picking_id, log_failure=False):
                log.state = "resolved"
