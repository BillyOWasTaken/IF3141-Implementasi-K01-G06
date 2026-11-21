from odoo import _, fields, models
from odoo.exceptions import UserError


class KintakunFulfillmentScan(models.TransientModel):
    _name = "kintakun.fulfillment.scan"
    _description = "Pindai Barang Fulfillment Check"

    picking_id = fields.Many2one("stock.picking", required=True, readonly=True)
    barcode = fields.Char(string="Barcode / Kode Produk")
    quantity = fields.Float(string="Jumlah", default=1.0)
    last_message = fields.Char(readonly=True)

    def _find_product(self):
        self.ensure_one()
        code = (self.barcode or "").strip()
        if not code:
            raise UserError(_("Pindai atau ketik barcode produk."))
        product = self.env["product.product"].search(
            ["|", ("barcode", "=", code), ("default_code", "=", code)], limit=1
        )
        if not product:
            raise UserError(_("Barcode '%s' tidak dikenali.", code))
        return product

    def action_scan(self):
        self.ensure_one()
        picking = self.picking_id
        if picking.kintakun_check_state != "checking":
            raise UserError(_("Mulai pemeriksaan terlebih dahulu."))
        product = self._find_product()
        line = picking.kintakun_check_line_ids.filtered(
            lambda check: check.product_id == product
        )[:1]
        if not line:
            raise UserError(
                _(
                    "Produk '%(product)s' tidak terdapat pada rincian SO %(order)s. "
                    "Barang tidak dihitung sebagai siap kirim.",
                    product=product.display_name,
                    order=picking.sale_id.name or picking.origin,
                )
            )
        if line.qty_checked + self.quantity > line.qty_demand:
            raise UserError(
                _(
                    "Kuantitas '%(product)s' melebihi kuantitas SO (%(demand)s).",
                    product=product.display_name,
                    demand=line.qty_demand,
                )
            )
        line.write({"qty_checked": line.qty_checked + self.quantity, "product_ok": True})
        next_scan = self.create(
            {
                "picking_id": picking.id,
                "last_message": _(
                    "%(product)s: %(checked)s dari %(demand)s",
                    product=product.display_name,
                    checked=line.qty_checked,
                    demand=line.qty_demand,
                ),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Pindai Barang"),
            "res_model": self._name,
            "res_id": next_scan.id,
            "view_mode": "form",
            "target": "new",
        }
