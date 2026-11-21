from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    kintakun_tier = fields.Selection(
        [("reguler", "Reguler"), ("prioritas", "Prioritas")], string="Tier Agen Kintakun"
    )


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    kintakun_rule_id = fields.Many2one(
        "kintakun.pricing.rule", string="Aturan Harga Kintakun", ondelete="cascade", index=True
    )
