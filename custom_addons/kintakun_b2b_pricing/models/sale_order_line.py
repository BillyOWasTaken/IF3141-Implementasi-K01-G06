from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

LOCKED_PRICE_FIELDS = ("price_unit", "discount")


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    kintakun_motif = fields.Char(related="product_id.kintakun_motif", string="Motif")
    kintakun_size = fields.Char(related="product_id.kintakun_size", string="Ukuran")
    kintakun_stock_available = fields.Float(
        string="Stok Tersedia",
        compute="_compute_kintakun_stock_available",
        digits="Product Unit of Measure",
    )

    @api.depends("product_id")
    def _compute_kintakun_stock_available(self):
        for line in self:
            line.kintakun_stock_available = line.product_id.sudo().free_qty

    @api.constrains("product_uom_qty")
    def _check_kintakun_quantity(self):
        for line in self:
            if (
                line.order_id.kintakun_is_b2b
                and line.order_id.state in ("draft", "sent")
                and not line.display_type
                and line.product_uom_qty <= 0
            ):
                raise ValidationError(
                    _("Kuantitas '%s' harus lebih besar dari nol.", line.product_id.display_name)
                )

    @api.onchange("product_id", "product_uom_qty")
    def _onchange_kintakun_stock_warning(self):
        if not self.order_id.kintakun_is_b2b or not self.product_id:
            return {}
        if self.product_id.type != "product":
            return {}
        available = self.product_id.sudo().free_qty
        if self.product_uom_qty > available:
            return {
                "warning": {
                    "title": _("Stok tidak mencukupi"),
                    "message": _(
                        "Kuantitas %(qty)s untuk '%(product)s' melampaui stok tersedia "
                        "(%(available)s). Pesanan tetap dapat disimpan, tetapi pengiriman "
                        "akan menunggu stok.",
                        qty=self.product_uom_qty,
                        product=self.product_id.display_name,
                        available=available,
                    ),
                }
            }
        return {}

    def _kintakun_price_locked(self):
        return not (self.env.su or self.env.context.get("kintakun_pricing_engine"))

    @api.model_create_multi
    def create(self, vals_list):
        if self._kintakun_price_locked():
            order_ids = [vals["order_id"] for vals in vals_list if vals.get("order_id")]
            b2b_ids = set(self.env["sale.order"].browse(order_ids).filtered("kintakun_is_b2b").ids)
            for vals in vals_list:
                if vals.get("order_id") in b2b_ids:
                    for field in LOCKED_PRICE_FIELDS:
                        vals.pop(field, None)
        return super().create(vals_list)

    def write(self, vals):
        if self._kintakun_price_locked() and set(LOCKED_PRICE_FIELDS) & set(vals):
            b2b_lines = self.filtered(lambda line: line.order_id.kintakun_is_b2b)
            if b2b_lines:
                locked_vals = {k: v for k, v in vals.items() if k not in LOCKED_PRICE_FIELDS}
                res = super(SaleOrderLine, b2b_lines).write(locked_vals) if locked_vals else True
                others = self - b2b_lines
                if others:
                    super(SaleOrderLine, others).write(vals)
                return res
        return super().write(vals)
