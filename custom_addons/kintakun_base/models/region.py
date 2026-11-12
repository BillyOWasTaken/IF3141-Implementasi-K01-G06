from odoo import api, fields, models


class KintakunRegion(models.Model):
    _name = "kintakun.region"
    _description = "Wilayah Agen"
    _order = "name"

    name = fields.Char(string="Nama Wilayah", required=True)
    code = fields.Char(string="Kode", required=True)
    active = fields.Boolean(default=True)
    agent_ids = fields.One2many("res.partner", "agent_region_id", string="Agen")
    agent_count = fields.Integer(string="Jumlah Agen", compute="_compute_agent_count")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Kode wilayah harus unik."),
    ]

    @api.depends("agent_ids")
    def _compute_agent_count(self):
        for region in self:
            region.agent_count = len(region.agent_ids)
