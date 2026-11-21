import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.kintakun_base.models.res_partner import AGENT_TIERS

from .pricing_rule import TIER_PRICELISTS

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    kintakun_is_b2b = fields.Boolean(
        string="Pesanan Agen B2B", compute="_compute_kintakun_pricing", store=True
    )
    kintakun_agent_tier = fields.Selection(
        AGENT_TIERS, string="Tier Agen", compute="_compute_kintakun_pricing", store=True
    )
    kintakun_agent_region_id = fields.Many2one(
        "kintakun.region", string="Wilayah Agen", compute="_compute_kintakun_pricing", store=True
    )
    kintakun_tier_rule_id = fields.Many2one(
        "kintakun.pricing.rule",
        string="Aturan Diskon Tier",
        compute="_compute_kintakun_pricing",
        store=True,
    )
    kintakun_promo_rule_id = fields.Many2one(
        "kintakun.pricing.rule",
        string="Aturan Promo",
        compute="_compute_kintakun_pricing",
        store=True,
    )
    kintakun_tier_discount = fields.Float(
        string="Diskon Tier (%)", compute="_compute_kintakun_pricing", store=True
    )
    kintakun_promo_discount = fields.Float(
        string="Diskon Promo (%)", compute="_compute_kintakun_pricing", store=True
    )
    kintakun_priority = fields.Selection(
        [("0", "Normal"), ("1", "Prioritas")],
        string="Priority Star",
        compute="_compute_kintakun_pricing",
        store=True,
    )
    kintakun_pricing_state = fields.Selection(
        [("draft", "Quotation Draft"), ("applied", "Pricelist Applied")],
        string="Status Harga",
        compute="_compute_kintakun_pricing_state",
        store=True,
    )
    kintakun_amount_gross = fields.Monetary(
        string="Total Sebelum Diskon", compute="_compute_kintakun_amounts", store=True
    )
    kintakun_tier_discount_amount = fields.Monetary(
        string="Potongan Tier", compute="_compute_kintakun_amounts", store=True
    )
    kintakun_promo_discount_amount = fields.Monetary(
        string="Potongan Promo", compute="_compute_kintakun_amounts", store=True
    )
    kintakun_quota_exceeded = fields.Boolean(
        string="Kuota Wilayah Terlampaui", compute="_compute_kintakun_quota"
    )
    kintakun_quota_message = fields.Char(string="Peringatan Kuota", compute="_compute_kintakun_quota")
    kintakun_queue_number = fields.Integer(string="No. Antrean", copy=False, readonly=True)
    kintakun_sync_log_ids = fields.One2many("kintakun.sync.log", "sale_id", string="Log Sinkronisasi")
    kintakun_sync_log_count = fields.Integer(compute="_compute_kintakun_sync_log_count")
    kintakun_sync_failed = fields.Boolean(compute="_compute_kintakun_sync_log_count")

    @api.depends("partner_id", "date_order")
    def _compute_kintakun_pricing(self):
        Rule = self.env["kintakun.pricing.rule"]
        for order in self:
            if order.state not in ("draft", "sent"):
                continue
            partner = order.partner_id.commercial_partner_id
            if not partner.is_kintakun_agent:
                order.update(
                    {
                        "kintakun_is_b2b": False,
                        "kintakun_agent_tier": False,
                        "kintakun_agent_region_id": False,
                        "kintakun_tier_rule_id": False,
                        "kintakun_promo_rule_id": False,
                        "kintakun_tier_discount": 0.0,
                        "kintakun_promo_discount": 0.0,
                        "kintakun_priority": "0",
                    }
                )
                continue
            date = fields.Date.context_today(order, order.date_order)
            tier_rule, promo_rule = Rule._find_rules(partner, date)
            order.update(
                {
                    "kintakun_is_b2b": True,
                    "kintakun_agent_tier": partner.agent_tier,
                    "kintakun_agent_region_id": partner.agent_region_id.id,
                    "kintakun_tier_rule_id": tier_rule.id,
                    "kintakun_promo_rule_id": promo_rule.id,
                    "kintakun_tier_discount": tier_rule.discount_percent,
                    "kintakun_promo_discount": promo_rule.discount_percent,
                    "kintakun_priority": "1" if partner.agent_tier == "prioritas" else "0",
                }
            )

    def _kintakun_expected_pricelist(self):
        self.ensure_one()
        if not self.kintakun_agent_tier:
            return self.env["product.pricelist"]
        return self.env.ref(TIER_PRICELISTS[self.kintakun_agent_tier])

    @api.depends("kintakun_is_b2b", "kintakun_tier_rule_id", "pricelist_id")
    def _compute_kintakun_pricing_state(self):
        for order in self:
            if not order.kintakun_is_b2b:
                order.kintakun_pricing_state = False
            elif (
                order.kintakun_tier_rule_id
                and order.pricelist_id == order._kintakun_expected_pricelist()
            ):
                order.kintakun_pricing_state = "applied"
            else:
                order.kintakun_pricing_state = "draft"

    @api.depends(
        "order_line.price_unit",
        "order_line.product_uom_qty",
        "kintakun_tier_discount",
        "kintakun_promo_discount",
    )
    def _compute_kintakun_amounts(self):
        for order in self:
            lines = order.order_line.filtered(lambda line: not line.display_type)
            gross = sum(line.price_unit * line.product_uom_qty for line in lines)
            currency = order.currency_id or order.company_id.currency_id
            order.kintakun_amount_gross = gross
            order.kintakun_tier_discount_amount = currency.round(
                gross * order.kintakun_tier_discount / 100
            )
            order.kintakun_promo_discount_amount = currency.round(
                gross * order.kintakun_promo_discount / 100
            )

    def _kintakun_order_qty(self):
        self.ensure_one()
        return sum(
            self.order_line.filtered(lambda line: not line.display_type).mapped("product_uom_qty")
        )

    def _kintakun_quota_used(self, rule):
        self.ensure_one()
        domain = rule._order_domain() + [
            ("kintakun_agent_region_id", "=", self.kintakun_agent_region_id.id)
        ]
        if self._origin.id:
            domain.append(("id", "!=", self._origin.id))
        orders = self.env["sale.order"].sudo().search(domain)
        return sum(order._kintakun_order_qty() for order in orders)

    @api.depends(
        "order_line.product_uom_qty",
        "kintakun_tier_rule_id",
        "kintakun_promo_rule_id",
        "kintakun_agent_region_id",
        "state",
    )
    def _compute_kintakun_quota(self):
        for order in self:
            order.kintakun_quota_exceeded = False
            order.kintakun_quota_message = False
            if not order.kintakun_is_b2b or order.state not in ("draft", "sent"):
                continue
            qty = order._kintakun_order_qty()
            rules = order.kintakun_tier_rule_id | order.kintakun_promo_rule_id
            for rule in rules.filtered("region_quota"):
                remaining = rule.region_quota - order._kintakun_quota_used(rule)
                if qty > remaining:
                    order.kintakun_quota_exceeded = True
                    order.kintakun_quota_message = _(
                        "Kuota wilayah %(region)s pada aturan '%(rule)s' terlampaui: "
                        "sisa kuota %(remaining)s pcs, pesanan %(qty)s pcs.",
                        region=order.kintakun_agent_region_id.name,
                        rule=rule.name,
                        remaining=int(max(remaining, 0)),
                        qty=int(qty),
                    )
                    break

    def _compute_kintakun_sync_log_count(self):
        for order in self:
            logs = order.sudo().kintakun_sync_log_ids
            order.kintakun_sync_log_count = len(logs)
            order.kintakun_sync_failed = any(log.state == "failed" for log in logs)

    def action_kintakun_reprice(self):
        orders = self.filtered(lambda o: o.kintakun_is_b2b and o.state in ("draft", "sent"))
        orders._compute_kintakun_pricing()
        for order in orders:
            order.pricelist_id = order._kintakun_expected_pricelist()
        orders.with_context(kintakun_pricing_engine=True)._recompute_prices()
        return True

    def _kintakun_check_before_confirm(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if not partner.active:
                raise UserError(_("Agen '%s' tidak aktif.", partner.name))
            if not order.order_line.filtered(lambda line: not line.display_type):
                raise UserError(_("Pesanan %s belum memiliki baris produk.", order.name))
            rule = order.kintakun_tier_rule_id
            if not rule or rule.state != "approved" or not rule.active:
                raise UserError(
                    _(
                        "Pesanan %s belum memiliki aturan harga tier yang disetujui Direktur "
                        "Utama. Klik 'Hitung Ulang Harga' atau hubungi Manajer Sales.",
                        order.name,
                    )
                )
            if order.pricelist_id != order._kintakun_expected_pricelist():
                raise UserError(
                    _(
                        "Pesanan %(order)s harus memakai pricelist '%(pricelist)s'. "
                        "Klik 'Hitung Ulang Harga'.",
                        order=order.name,
                        pricelist=order._kintakun_expected_pricelist().name,
                    )
                )
            if order.kintakun_quota_exceeded:
                raise UserError(order.kintakun_quota_message)

    def action_confirm(self):
        b2b_orders = self.filtered(lambda o: o.kintakun_is_b2b and o.state in ("draft", "sent"))
        b2b_orders._kintakun_check_before_confirm()
        b2b_orders.write({"picking_policy": "one"})
        res = super().action_confirm()
        for order in b2b_orders.filtered(lambda o: o.state == "sale"):
            order.kintakun_queue_number = int(
                self.env["ir.sequence"].sudo().next_by_code("kintakun.so.queue")
            )
            order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")).sudo().write(
                {"priority": order.kintakun_priority}
            )
        return res

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.kintakun_is_b2b:
            vals["kintakun_sale_id"] = self.id
        return vals

    def _kintakun_sync_invoice(self, picking=None, log_failure=True):
        self.ensure_one()
        Log = self.env["kintakun.sync.log"]
        try:
            with self.env.cr.savepoint():
                invoice = self.sudo()._create_invoices()
        except (UserError, ValidationError) as error:
            _logger.warning("Sinkronisasi faktur %s gagal: %s", self.name, error)
            if log_failure:
                Log._log(
                    "invoice",
                    "failed",
                    _("Draf faktur gagal dibuat: %s", error),
                    sale=self,
                    picking=picking,
                )
            return False
        for move in invoice:
            Log._log(
                "invoice",
                "success",
                _(
                    "Draf faktur piutang dibuat senilai %(amount)s dari %(order)s.",
                    amount=move.currency_id.format(move.amount_total),
                    order=self.name,
                ),
                sale=self,
                picking=picking,
                invoice=move,
            )
        return invoice

    def action_view_kintakun_sync_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Log Sinkronisasi"),
            "res_model": "kintakun.sync.log",
            "view_mode": "tree,form",
            "domain": [("sale_id", "=", self.id)],
        }
