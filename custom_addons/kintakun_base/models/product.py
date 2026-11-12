from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    kintakun_brand = fields.Selection(
        [
            ("lite", "Kintakun Lite"),
            ("deluxe", "Kintakun D'Luxe"),
            ("luxury", "Kintakun Luxury"),
            ("beglance", "Kintakun Beglance"),
        ],
        string="Merek",
    )
    kintakun_motif = fields.Char(string="Motif")
    kintakun_size = fields.Char(string="Ukuran")
