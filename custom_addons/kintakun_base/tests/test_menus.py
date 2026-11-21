from odoo.tests import tagged

from .common import KintakunCommon

SECTIONS = ("sales", "procurement", "warehouse", "finance", "monitoring", "master", "config")


@tagged("post_install", "-at_install")
class TestMenus(KintakunCommon):
    def _visible_sections(self, user):
        visible = self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()
        return {
            section
            for section in SECTIONS
            if self.env.ref(f"kintakun_base.menu_kintakun_{section}").id in visible
        }

    def test_admin_sees_every_section(self):
        admin = self.env.ref("base.user_admin")
        self.assertEqual(self._visible_sections(admin), set(SECTIONS))

    def test_sections_per_role(self):
        expected = {
            self.user_staf_sales: {"sales", "master"},
            self.user_manajer_sales: {"sales", "monitoring", "master"},
            self.user_staf_inventory: {"warehouse", "master"},
            self.user_manajer_procurement: {"procurement", "warehouse", "monitoring", "master"},
            self.user_manajer_finance: {"finance", "monitoring", "master"},
            self.user_direktur: {
                "sales", "procurement", "warehouse", "finance", "monitoring", "master",
            },
        }
        for user, sections in expected.items():
            self.assertEqual(self._visible_sections(user), sections, user.login)

    def test_every_leaf_menu_has_action(self):
        root = self.env.ref("kintakun_base.menu_kintakun_root")
        menus = self.env["ir.ui.menu"].search([("id", "child_of", root.id)])
        leaves = menus.filtered(lambda menu: not menu.child_id)
        self.assertTrue(leaves)
        self.assertFalse(leaves.filtered(lambda menu: not menu.action))
