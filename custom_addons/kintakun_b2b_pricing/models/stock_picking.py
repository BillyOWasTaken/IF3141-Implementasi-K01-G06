from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    kintakun_is_b2b = fields.Boolean(
        related="sale_id.kintakun_is_b2b", string="Pesanan Agen B2B", store=True
    )
    kintakun_agent_tier = fields.Selection(
        related="sale_id.kintakun_agent_tier", string="Tier Agen", store=True
    )
    kintakun_queue_number = fields.Integer(
        related="sale_id.kintakun_queue_number", string="No. Antrean", store=True
    )
    kintakun_check_state = fields.Selection(
        [
            ("waiting", "Menunggu Pemeriksaan"),
            ("checking", "Sedang Diperiksa"),
            ("failed", "Tidak Sesuai"),
            ("checked", "Lolos Pemeriksaan"),
            ("validated", "Tervalidasi"),
        ],
        string="Status Fulfillment Check",
        default="waiting",
        copy=False,
        tracking=True,
    )
    kintakun_check_line_ids = fields.One2many(
        "kintakun.fulfillment.check.line", "picking_id", string="Pemeriksaan Fisik", copy=False
    )
    kintakun_checker_id = fields.Many2one("res.users", string="Pemeriksa", copy=False, readonly=True)
    kintakun_check_date = fields.Datetime(string="Tanggal Pemeriksaan", copy=False, readonly=True)
    kintakun_check_note = fields.Text(string="Catatan Pemeriksaan", copy=False)

    def _kintakun_requires_check(self):
        self.ensure_one()
        return self.picking_type_code == "outgoing" and self.kintakun_is_b2b

    def _kintakun_moves(self):
        self.ensure_one()
        return self.move_ids.filtered(lambda m: m.state not in ("cancel", "done"))

    def action_kintakun_start_check(self):
        for picking in self:
            if not picking._kintakun_requires_check():
                raise UserError(_("Fulfillment check hanya untuk pengiriman pesanan agen B2B."))
            if picking.state != "assigned":
                raise UserError(
                    _("Pengiriman %s belum berstatus Ready; stok belum tersedia penuh.", picking.name)
                )
            if picking.kintakun_check_state not in ("waiting", "failed", "checked"):
                raise UserError(
                    _("Pemeriksaan %s sedang berjalan atau sudah selesai.", picking.name)
                )
            picking.kintakun_check_line_ids.sudo().unlink()
            self.env["kintakun.fulfillment.check.line"].create(
                [
                    {
                        "picking_id": picking.id,
                        "move_id": move.id,
                        "product_id": move.product_id.id,
                        "qty_demand": move.product_uom_qty,
                    }
                    for move in picking._kintakun_moves()
                ]
            )
            picking.write(
                {
                    "kintakun_check_state": "checking",
                    "kintakun_checker_id": self.env.user.id,
                    "kintakun_check_date": False,
                }
            )
        return True

    def action_kintakun_finish_check(self):
        for picking in self:
            if picking.kintakun_check_state != "checking":
                raise UserError(_("Mulai pemeriksaan %s terlebih dahulu.", picking.name))
            lines = picking.kintakun_check_line_ids
            mismatches = lines.filtered(lambda line: line.result != "match")
            values = {
                "kintakun_checker_id": self.env.user.id,
                "kintakun_check_date": fields.Datetime.now(),
            }
            if mismatches or not lines:
                reasons = [line._mismatch_reason() for line in mismatches]
                picking.write(dict(values, kintakun_check_state="failed"))
                picking._message_log(
                    body=Markup("%s<ul>%s</ul>")
                    % (
                        _("Fulfillment check TIDAK SESUAI; surat jalan ditahan."),
                        Markup().join(Markup("<li>%s</li>") % reason for reason in reasons),
                    )
                )
                continue
            for line in lines:
                line.move_id.write({"quantity": line.qty_checked, "picked": True})
            picking.write(dict(values, kintakun_check_state="checked"))
            picking._message_log(
                body=_("Fulfillment check LOLOS: motif, ukuran, dan kuantitas sesuai rincian SO.")
            )
        return True

    def _kintakun_check_ready_to_validate(self):
        for picking in self.filtered(lambda p: p._kintakun_requires_check()):
            if picking.kintakun_check_state != "checked":
                raise UserError(
                    _(
                        "Pengiriman %s belum lolos fulfillment check. Surat jalan hanya "
                        "dapat diterbitkan setelah motif, ukuran, dan kuantitas sesuai SO.",
                        picking.name,
                    )
                )
            for move in picking._kintakun_moves():
                if float_compare(
                    move.quantity,
                    move.product_uom_qty,
                    precision_rounding=move.product_uom.rounding,
                ):
                    raise UserError(
                        _(
                            "Kuantitas '%(product)s' (%(qty)s) tidak sama dengan kuantitas "
                            "SO (%(demand)s). Ulangi fulfillment check.",
                            product=move.product_id.display_name,
                            qty=move.quantity,
                            demand=move.product_uom_qty,
                        )
                    )

    def button_validate(self):
        self._kintakun_check_ready_to_validate()
        checked = self.filtered(lambda p: p._kintakun_requires_check())
        res = super().button_validate()
        for picking in checked.filtered(lambda p: p.state == "done"):
            picking.kintakun_check_state = "validated"
            picking._message_log(
                body=_(
                    "Surat jalan %(name)s diterbitkan oleh %(user)s pada %(date)s.",
                    name=picking.name,
                    user=self.env.user.name,
                    date=fields.Datetime.context_timestamp(picking, fields.Datetime.now()).strftime(
                        "%d/%m/%Y %H:%M"
                    ),
                )
            )
        return res

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if picking.state == "done" and picking._kintakun_requires_check():
                picking._kintakun_sync_after_delivery()
        return res

    def _kintakun_sync_after_delivery(self):
        self.ensure_one()
        details = ", ".join(
            _(
                "%(product)s -%(qty)s (sisa %(left)s)",
                product=move.product_id.display_name,
                qty=move.quantity,
                left=move.product_id.sudo().qty_available,
            )
            for move in self.move_ids.filtered(lambda m: m.state == "done")
        )
        self.env["kintakun.sync.log"]._log(
            "stock",
            "success",
            _("Stok dipotong oleh %(picking)s: %(details)s", picking=self.name, details=details),
            sale=self.sale_id,
            picking=self,
        )
        self.sale_id._kintakun_sync_invoice(self)

    def action_kintakun_open_scan(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Pindai Barang"),
            "res_model": "kintakun.fulfillment.scan",
            "view_mode": "form",
            "target": "new",
            "context": {"default_picking_id": self.id},
        }
