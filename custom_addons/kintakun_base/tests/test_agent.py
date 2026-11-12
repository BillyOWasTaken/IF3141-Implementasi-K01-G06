from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import KintakunCommon


@tagged("post_install", "-at_install")
class TestAgentMaster(KintakunCommon):
    def test_agent_code_generated(self):
        self.assertTrue(self.agent_reguler.agent_code)
        self.assertNotEqual(self.agent_reguler.agent_code, self.agent_prioritas.agent_code)

    def test_agent_requires_region(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create({"name": "Tanpa Wilayah", "is_kintakun_agent": True})

    def test_staf_sales_updates_contact_only(self):
        agent = self.agent_reguler.with_user(self.user_staf_sales)
        agent.write({"phone": "0812-0000-1111", "street": "Jl. Baru No. 1"})
        self.assertEqual(self.agent_reguler.phone, "0812-0000-1111")
        with self.assertRaises(AccessError):
            agent.write({"agent_tier": "prioritas"})
        with self.assertRaises(AccessError):
            agent.write({"agent_region_id": self.region_jakarta.id})
        self.assertEqual(self.agent_reguler.agent_tier, "reguler")

    def test_staf_sales_cannot_create_priority_agent(self):
        vals = {
            "name": "Agen Baru",
            "is_kintakun_agent": True,
            "agent_region_id": self.region_bandung.id,
        }
        Partner = self.env["res.partner"].with_user(self.user_staf_sales)
        self.assertEqual(Partner.create(vals).agent_tier, "reguler")
        with self.assertRaises(AccessError):
            Partner.create(dict(vals, name="Agen Baru 2", agent_tier="prioritas"))

    def test_manajer_sales_changes_tier(self):
        self.agent_reguler.with_user(self.user_manajer_sales).write({"agent_tier": "prioritas"})
        self.assertEqual(self.agent_reguler.agent_tier, "prioritas")

    def test_staf_sales_cannot_manage_regions(self):
        with self.assertRaises(AccessError):
            self.env["kintakun.region"].with_user(self.user_staf_sales).create(
                {"name": "Wilayah Liar", "code": "X"}
            )

    def test_company_uses_rupiah(self):
        self.assertEqual(self.env.company.currency_id, self.env.ref("base.IDR"))
        self.assertEqual(self.env.company.country_id, self.env.ref("base.id"))
        order = self.env["sale.order"].create({"partner_id": self.agent_reguler.id})
        self.assertEqual(order.currency_id, self.env.ref("base.IDR"))
