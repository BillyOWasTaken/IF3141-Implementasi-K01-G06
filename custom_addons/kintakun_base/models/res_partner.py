from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

AGENT_TIERS = [("reguler", "Reguler"), ("prioritas", "Prioritas")]
MANAGER_GROUPS = ("kintakun_base.group_manajer_sales", "kintakun_base.group_manajer_it")


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_kintakun_agent = fields.Boolean(string="Agen B2B", tracking=True)
    agent_code = fields.Char(string="Kode Agen", copy=False, tracking=True)
    agent_tier = fields.Selection(
        AGENT_TIERS, string="Tier Agen", default="reguler", tracking=True
    )
    agent_region_id = fields.Many2one(
        "kintakun.region", string="Wilayah", tracking=True, ondelete="restrict"
    )

    _sql_constraints = [
        ("agent_code_uniq", "unique(agent_code)", "Kode agen harus unik."),
    ]

    @api.constrains("is_kintakun_agent", "agent_tier", "agent_region_id")
    def _check_agent_master(self):
        for partner in self:
            if partner.is_kintakun_agent and not (
                partner.agent_tier and partner.agent_region_id
            ):
                raise ValidationError(
                    _("Agen B2B '%s' wajib memiliki tier dan wilayah.", partner.name)
                )

    def _kintakun_is_master_manager(self):
        return self.env.su or any(self.env.user.has_group(g) for g in MANAGER_GROUPS)

    @api.model_create_multi
    def create(self, vals_list):
        is_manager = self._kintakun_is_master_manager()
        for vals in vals_list:
            if not vals.get("is_kintakun_agent"):
                continue
            if vals.get("agent_tier", "reguler") != "reguler" and not is_manager:
                raise AccessError(
                    _("Hanya Manajer Sales yang dapat menetapkan agen prioritas.")
                )
            if not vals.get("agent_code"):
                vals["agent_code"] = self.env["ir.sequence"].next_by_code(
                    "kintakun.agent"
                )
        return super().create(vals_list)

    def write(self, vals):
        if not self._kintakun_is_master_manager():
            for field in ("agent_tier", "agent_region_id"):
                if field not in vals:
                    continue
                changed = self.filtered(
                    lambda p, f=field: p.is_kintakun_agent
                    and (p[f].id if f == "agent_region_id" else p[f]) != vals[f]
                )
                if changed:
                    raise AccessError(
                        _(
                            "Tier dan wilayah agen hanya dapat diubah oleh "
                            "Manajer Sales."
                        )
                    )
        return super().write(vals)
