from datetime import datetime, time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

GROUP_MANAGER = "kintakun_base.group_manajer_sales"
GROUP_DIRECTOR = "kintakun_base.group_direktur"
TIER_PRICELISTS = {
    "reguler": "kintakun_b2b_pricing.pricelist_agen_reguler",
    "prioritas": "kintakun_b2b_pricing.pricelist_agen_prioritas",
}
PARAMETER_FIELDS = {
    "name",
    "rule_type",
    "agent_tier",
    "discount_percent",
    "region_quota",
    "date_start",
    "date_end",
}
TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"approved", "rejected"},
    "rejected": {"draft"},
    "approved": set(),
}
TRANSITION_GROUP = {
    "submitted": GROUP_MANAGER,
    "draft": GROUP_MANAGER,
    "approved": GROUP_DIRECTOR,
    "rejected": GROUP_DIRECTOR,
}


class KintakunPricingRule(models.Model):
    _name = "kintakun.pricing.rule"
    _description = "Aturan Harga Kintakun"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "rule_type desc, agent_tier, id desc"

    name = fields.Char(string="Nama Aturan", required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    rule_type = fields.Selection(
        [("tier", "Diskon Tier Agen"), ("promo", "Promo Musiman")],
        string="Jenis Aturan",
        required=True,
        default="tier",
        tracking=True,
    )
    agent_tier = fields.Selection(
        [("all", "Semua Tier"), ("reguler", "Reguler"), ("prioritas", "Prioritas")],
        string="Tier Agen",
        required=True,
        default="reguler",
        tracking=True,
    )
    discount_percent = fields.Float(
        string="Diskon (%)", required=True, digits=(5, 2), tracking=True
    )
    region_quota = fields.Integer(
        string="Kuota per Wilayah (pcs)",
        tracking=True,
        help="Batas total kuantitas sales order per wilayah agen yang boleh memakai aturan ini. "
        "0 berarti tanpa batas.",
    )
    date_start = fields.Date(string="Periode Mulai", tracking=True)
    date_end = fields.Date(string="Periode Selesai", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draf"),
            ("submitted", "Menunggu Persetujuan"),
            ("approved", "Disetujui"),
            ("rejected", "Ditolak"),
        ],
        string="Status Persetujuan",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    proposed_by_id = fields.Many2one("res.users", string="Diajukan Oleh", copy=False, readonly=True)
    approved_by_id = fields.Many2one(
        "res.users", string="Diputuskan Oleh", copy=False, readonly=True
    )
    approved_date = fields.Datetime(string="Tanggal Keputusan", copy=False, readonly=True)
    rejection_reason = fields.Text(string="Alasan Penolakan", copy=False, tracking=True)
    revision_of_id = fields.Many2one(
        "kintakun.pricing.rule", string="Revisi Dari", copy=False, readonly=True, ondelete="set null"
    )
    pricelist_item_ids = fields.One2many(
        "product.pricelist.item", "kintakun_rule_id", string="Item Pricelist", readonly=True
    )
    quota_used = fields.Float(string="Kuantitas Terpakai", compute="_compute_quota_used")
    order_count = fields.Integer(string="Jumlah SO", compute="_compute_quota_used")

    @api.constrains("discount_percent", "region_quota")
    def _check_values(self):
        for rule in self:
            if not 0 < rule.discount_percent <= 100:
                raise ValidationError(_("Diskon harus lebih dari 0% dan paling besar 100%."))
            if rule.region_quota < 0:
                raise ValidationError(_("Kuota wilayah tidak boleh negatif."))

    @api.constrains("rule_type", "agent_tier", "date_start", "date_end")
    def _check_scope(self):
        for rule in self:
            if rule.rule_type == "tier":
                if rule.agent_tier == "all":
                    raise ValidationError(
                        _("Aturan diskon tier harus memilih tier Reguler atau Prioritas.")
                    )
                if rule.date_start or rule.date_end:
                    raise ValidationError(_("Aturan diskon tier tidak memakai periode."))
            elif not (rule.date_start and rule.date_end):
                raise ValidationError(_("Promo musiman wajib memiliki periode mulai dan selesai."))
            if rule.date_start and rule.date_end and rule.date_start > rule.date_end:
                raise ValidationError(_("Periode mulai tidak boleh setelah periode selesai."))

    @api.onchange("rule_type")
    def _onchange_rule_type(self):
        if self.rule_type == "tier":
            self.date_start = self.date_end = False
            if self.agent_tier == "all":
                self.agent_tier = "reguler"

    def _check_group(self, group, message):
        if not self.env.su and not self.env.user.has_group(group):
            raise AccessError(message)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                if vals.get("state", "draft") != "draft":
                    raise AccessError(_("Aturan harga baru harus dimulai dari status Draf."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            if "state" in vals:
                self._check_transition(vals["state"])
            locked = self.filtered(lambda r: r.state != "draft")
            if locked and PARAMETER_FIELDS & set(vals):
                raise UserError(
                    _(
                        "Parameter aturan hanya dapat diubah saat berstatus Draf. "
                        "Gunakan 'Buat Revisi' untuk mengubah aturan yang sudah diajukan."
                    )
                )
            if "active" in vals and locked:
                self._check_group(
                    GROUP_DIRECTOR,
                    _("Hanya Direktur Utama yang dapat mengarsipkan aturan yang sudah diajukan."),
                )
        res = super().write(vals)
        if "active" in vals and self.filtered(lambda r: r.state == "approved"):
            self._sync_pricelists()
        return res

    def unlink(self):
        if not self.env.su and any(rule.state != "draft" for rule in self):
            raise UserError(_("Hanya aturan berstatus Draf yang dapat dihapus."))
        return super().unlink()

    def _check_transition(self, target):
        self._check_group(
            TRANSITION_GROUP[target],
            _("Anda tidak berwenang mengubah status aturan harga menjadi '%s'.", target),
        )
        for rule in self:
            if rule.state != target and target not in TRANSITIONS[rule.state]:
                raise UserError(
                    _(
                        "Aturan '%(name)s' tidak dapat berpindah dari %(src)s ke %(dst)s.",
                        name=rule.name,
                        src=rule.state,
                        dst=target,
                    )
                )

    def action_submit(self):
        self.write({"state": "submitted", "proposed_by_id": self.env.user.id})
        for rule in self:
            rule._message_log(body=_("Aturan harga diajukan untuk persetujuan Direktur Utama."))
        return True

    def action_approve(self):
        self.write(
            {
                "state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            }
        )
        for rule in self:
            if rule.revision_of_id.active:
                rule.revision_of_id.sudo().active = False
                rule.revision_of_id._message_log(
                    body=_("Digantikan oleh revisi '%s' yang telah disetujui.", rule.name)
                )
            rule._message_log(body=_("Aturan harga disetujui dan pricelist agen diaktifkan."))
        self._sync_pricelists()
        return True

    def action_reject(self):
        self.write(
            {
                "state": "rejected",
                "approved_by_id": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            }
        )
        for rule in self:
            rule._message_log(body=_("Aturan harga ditolak. %s", rule.rejection_reason or ""))
        return True

    def action_reset_draft(self):
        return self.write({"state": "draft"})

    def action_create_revision(self):
        self.ensure_one()
        self._check_group(
            GROUP_MANAGER, _("Hanya Manajer Sales yang dapat membuat revisi aturan harga.")
        )
        revision = self.copy({"name": _("%s (Revisi)", self.name)})
        revision.sudo().revision_of_id = self
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": revision.id,
            "view_mode": "form",
        }

    @api.model
    def _approved_domain(self):
        return [("state", "=", "approved"), ("active", "=", True)]

    @api.model
    def _tier_rule(self, tier):
        return self.sudo().search(
            self._approved_domain() + [("rule_type", "=", "tier"), ("agent_tier", "=", tier)],
            order="approved_date desc, id desc",
            limit=1,
        )

    @api.model
    def _find_rules(self, partner, date):
        tier = partner.agent_tier
        promo = self.sudo().search(
            self._approved_domain()
            + [
                ("rule_type", "=", "promo"),
                ("agent_tier", "in", ("all", tier)),
                ("date_start", "<=", date),
                ("date_end", ">=", date),
            ],
            order="discount_percent desc, id desc",
            limit=1,
        )
        return self._tier_rule(tier), promo

    @api.model
    def _local_bound(self, day, end=False):
        tz = pytz.timezone(self.env.user.tz or "Asia/Jakarta")
        moment = datetime.combine(day, time.max.replace(microsecond=0) if end else time.min)
        return tz.localize(moment).astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _sync_pricelists(self):
        Item = self.env["product.pricelist.item"].sudo()
        for tier, xmlid in TIER_PRICELISTS.items():
            pricelist = self.env.ref(xmlid).sudo()
            pricelist.item_ids.filtered("kintakun_rule_id").unlink()
            tier_rule = self._tier_rule(tier)
            base = tier_rule.discount_percent
            values = []
            if tier_rule:
                values.append(
                    {
                        "pricelist_id": pricelist.id,
                        "applied_on": "3_global",
                        "compute_price": "percentage",
                        "percent_price": base,
                        "kintakun_rule_id": tier_rule.id,
                    }
                )
            promos = self.sudo().search(
                self._approved_domain()
                + [("rule_type", "=", "promo"), ("agent_tier", "in", ("all", tier))],
                order="discount_percent asc, id asc",
            )
            for promo in promos:
                values.append(
                    {
                        "pricelist_id": pricelist.id,
                        "applied_on": "3_global",
                        "compute_price": "percentage",
                        "percent_price": min(base + promo.discount_percent, 100.0),
                        "date_start": self._local_bound(promo.date_start),
                        "date_end": self._local_bound(promo.date_end, end=True),
                        "kintakun_rule_id": promo.id,
                    }
                )
            Item.create(values)
        return True

    def _order_domain(self):
        self.ensure_one()
        return [
            ("state", "=", "sale"),
            "|",
            ("kintakun_tier_rule_id", "=", self.id),
            ("kintakun_promo_rule_id", "=", self.id),
        ]

    def _compute_quota_used(self):
        for rule in self:
            orders = self.env["sale.order"].sudo().search(rule._order_domain())
            rule.order_count = len(orders)
            rule.quota_used = sum(order._kintakun_order_qty() for order in orders)

    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "sale.order",
            "view_mode": "tree,form",
            "domain": self._order_domain(),
        }
