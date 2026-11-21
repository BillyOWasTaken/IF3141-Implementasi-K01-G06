from odoo import api, fields, models

from .pricing_rule import TIER_PRICELISTS


class ResPartner(models.Model):
    _inherit = "res.partner"

    kintakun_receivable = fields.Monetary(
        string="Piutang Berjalan",
        compute="_compute_kintakun_receivable",
        currency_field="currency_id",
    )

    def _compute_kintakun_receivable(self):
        for partner in self:
            partner.kintakun_receivable = partner.sudo().credit

    def _kintakun_assign_pricelist(self):
        for partner in self.filtered(lambda p: p.is_kintakun_agent and p.agent_tier):
            pricelist = self.env.ref(TIER_PRICELISTS[partner.agent_tier])
            if partner.sudo().property_product_pricelist != pricelist:
                partner.sudo().property_product_pricelist = pricelist

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._kintakun_assign_pricelist()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if {"is_kintakun_agent", "agent_tier"} & set(vals):
            self._kintakun_assign_pricelist()
        return res
