from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class KintakunFulfillmentCheckLine(models.Model):
    _name = "kintakun.fulfillment.check.line"
    _description = "Baris Pemeriksaan Fisik Barang"
    _order = "picking_id, id"

    picking_id = fields.Many2one(
        "stock.picking", string="Pengiriman", required=True, ondelete="cascade", index=True
    )
    move_id = fields.Many2one("stock.move", string="Pergerakan Stok", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Produk", required=True)
    kintakun_motif = fields.Char(related="product_id.kintakun_motif", string="Motif")
    kintakun_size = fields.Char(related="product_id.kintakun_size", string="Ukuran")
    qty_demand = fields.Float(
        string="Kuantitas SO", digits="Product Unit of Measure", readonly=True
    )
    qty_checked = fields.Float(string="Kuantitas Fisik", digits="Product Unit of Measure")
    product_ok = fields.Boolean(string="Motif & Ukuran Sesuai")
    note = fields.Char(string="Catatan")
    result = fields.Selection(
        [("pending", "Belum Diperiksa"), ("match", "Cocok"), ("mismatch", "Tidak Cocok")],
        string="Hasil",
        compute="_compute_result",
        store=True,
    )

    @api.depends("qty_checked", "qty_demand", "product_ok")
    def _compute_result(self):
        for line in self:
            precision = line.product_id.uom_id.rounding or 0.01
            same_qty = (
                float_compare(line.qty_checked, line.qty_demand, precision_rounding=precision)
                == 0
            )
            if not line.qty_checked and not line.product_ok:
                line.result = "pending"
            elif same_qty and line.product_ok:
                line.result = "match"
            else:
                line.result = "mismatch"

    def _mismatch_reason(self):
        self.ensure_one()
        reasons = []
        if not self.product_ok:
            reasons.append(_("motif/ukuran belum dinyatakan sesuai"))
        if self.result != "match" and self.qty_checked != self.qty_demand:
            reasons.append(
                _(
                    "kuantitas fisik %(checked)s tidak sama dengan kuantitas SO %(demand)s",
                    checked=self.qty_checked,
                    demand=self.qty_demand,
                )
            )
        return _("%(product)s: %(reasons)s", product=self.product_id.display_name,
                 reasons=", ".join(reasons))

    def write(self, vals):
        if not self.env.su and {"qty_checked", "product_ok", "note"} & set(vals):
            if any(line.picking_id.kintakun_check_state != "checking" for line in self):
                raise UserError(
                    _("Hasil pemeriksaan hanya dapat diubah saat status 'Sedang Diperiksa'.")
                )
        return super().write(vals)
