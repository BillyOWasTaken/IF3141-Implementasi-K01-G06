from odoo import api, fields, models

ROLE_GROUPS = [
    ("manajer_it", "Manajer IT", "kintakun_base.group_manajer_it"),
    ("direktur", "Direktur Utama", "kintakun_base.group_direktur"),
    ("manajer_sales", "Manajer Sales", "kintakun_base.group_manajer_sales"),
    ("staf_sales", "Staf Sales", "kintakun_base.group_staf_sales"),
    ("manajer_finance", "Manajer Finance", "kintakun_base.group_manajer_finance"),
    ("manajer_procurement", "Manajer Procurement", "kintakun_base.group_manajer_procurement"),
    ("manajer_inventory", "Manajer Inventory", "kintakun_base.group_manajer_inventory"),
    ("staf_inventory", "Staf Inventory", "kintakun_base.group_staf_inventory"),
]
PROTECTED_USERS = ("base.user_root", "base.user_admin")


class ResUsers(models.Model):
    _inherit = "res.users"

    kintakun_role = fields.Selection(
        [(key, label) for key, label, _xmlid in ROLE_GROUPS],
        string="Role Kintakun",
        compute="_compute_kintakun_role",
        inverse="_inverse_kintakun_role",
    )

    @api.depends("groups_id")
    def _compute_kintakun_role(self):
        groups = {key: self.env.ref(xmlid) for key, _label, xmlid in ROLE_GROUPS}
        for user in self:
            user.kintakun_role = next(
                (key for key, _label, _x in ROLE_GROUPS if groups[key] in user.groups_id), False
            )

    def _inverse_kintakun_role(self):
        roles = self.env["res.groups"].browse(
            [self.env.ref(xmlid).id for _key, _label, xmlid in ROLE_GROUPS]
        )
        keep = self.env.ref("base.group_user")
        removable = (roles | roles.trans_implied_ids) - keep - keep.trans_implied_ids
        protected = [self.env.ref(xmlid, raise_if_not_found=False) for xmlid in PROTECTED_USERS]
        for user in self:
            commands = []
            if user not in protected:
                commands += [(3, group.id) for group in removable & user.groups_id]
            if user.kintakun_role:
                xmlid = next(x for key, _label, x in ROLE_GROUPS if key == user.kintakun_role)
                commands.append((4, self.env.ref(xmlid).id))
            if commands:
                user.groups_id = commands
