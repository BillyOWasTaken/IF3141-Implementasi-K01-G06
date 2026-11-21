from odoo import fields, models, tools


class KintakunStockMonitor(models.Model):
    _name = "kintakun.stock.monitor"
    _description = "Pemantauan Stok dan Kebutuhan Barang"
    _auto = False
    _rec_name = "product_id"
    _order = "qty_shortage desc, qty_open_demand desc"

    product_id = fields.Many2one("product.product", string="Produk", readonly=True)
    kintakun_brand = fields.Selection(
        [
            ("lite", "Kintakun Lite"),
            ("deluxe", "Kintakun D'Luxe"),
            ("luxury", "Kintakun Luxury"),
            ("beglance", "Kintakun Beglance"),
        ],
        string="Merek",
        readonly=True,
    )
    kintakun_motif = fields.Char(string="Motif", readonly=True)
    kintakun_size = fields.Char(string="Ukuran", readonly=True)
    qty_on_hand = fields.Float(string="Stok Fisik", readonly=True)
    qty_reserved = fields.Float(string="Dialokasikan", readonly=True)
    qty_available = fields.Float(string="Stok Bebas", readonly=True)
    qty_open_demand = fields.Float(string="Pesanan Belum Terkirim", readonly=True)
    qty_delivered = fields.Float(string="Terkirim ke Agen", readonly=True)
    qty_shortage = fields.Float(string="Kebutuhan Pengadaan", readonly=True)
    stock_status = fields.Selection(
        [("ok", "Cukup"), ("low", "Menipis"), ("short", "Kurang")],
        string="Status Stok",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    pp.id AS id,
                    pp.id AS product_id,
                    pt.kintakun_brand,
                    pt.kintakun_motif,
                    pt.kintakun_size,
                    COALESCE(q.on_hand, 0) AS qty_on_hand,
                    COALESCE(q.reserved, 0) AS qty_reserved,
                    COALESCE(q.on_hand, 0) - COALESCE(q.reserved, 0) AS qty_available,
                    COALESCE(d.open_qty, 0) AS qty_open_demand,
                    COALESCE(d.delivered_qty, 0) AS qty_delivered,
                    GREATEST(COALESCE(d.open_qty, 0) - COALESCE(q.on_hand, 0), 0) AS qty_shortage,
                    CASE
                        WHEN COALESCE(d.open_qty, 0) > COALESCE(q.on_hand, 0) THEN 'short'
                        WHEN COALESCE(q.on_hand, 0) - COALESCE(q.reserved, 0) <= 10 THEN 'low'
                        ELSE 'ok'
                    END AS stock_status
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN (
                    SELECT sq.product_id,
                           SUM(sq.quantity) AS on_hand,
                           SUM(sq.reserved_quantity) AS reserved
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id
                ) q ON q.product_id = pp.id
                LEFT JOIN (
                    SELECT sol.product_id,
                           SUM(GREATEST(sol.product_uom_qty - sol.qty_delivered, 0)) AS open_qty,
                           SUM(sol.qty_delivered) AS delivered_qty
                    FROM sale_order_line sol
                    JOIN sale_order so ON so.id = sol.order_id
                    WHERE so.state = 'sale'
                      AND so.kintakun_is_b2b
                      AND sol.display_type IS NULL
                    GROUP BY sol.product_id
                ) d ON d.product_id = pp.id
                WHERE pp.active AND pt.active AND pt.type = 'product' AND pt.sale_ok
            )
            """
            % self._table
        )
