from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import B2BCommon


@tagged("post_install", "-at_install")
class TestPricingRule(B2BCommon):
    def _proposal(self, **values):
        vals = {
            "name": "Usulan Uji",
            "rule_type": "tier",
            "agent_tier": "reguler",
            "discount_percent": 6,
        }
        vals.update(values)
        return self.Rule.with_user(self.user_manajer_sales).create(vals)

    def _tier_percent(self, pricelist):
        items = pricelist.item_ids.filtered(lambda i: i.kintakun_rule_id and not i.date_start)
        return items.percent_price

    def test_agents_use_tier_pricelist(self):
        self.assertEqual(self.agent_reguler.property_product_pricelist, self.pricelist_reguler)
        self.assertEqual(self.agent_prioritas.property_product_pricelist, self.pricelist_prioritas)
        self.agent_reguler.with_user(self.user_manajer_sales).agent_tier = "prioritas"
        self.assertEqual(self.agent_reguler.property_product_pricelist, self.pricelist_prioritas)

    def test_approved_rules_activate_pricelist(self):
        self.assertEqual(self._tier_percent(self.pricelist_reguler), 5)
        self.assertEqual(self._tier_percent(self.pricelist_prioritas), 7)
        self.assertEqual(self.rule_reguler.pricelist_item_ids.pricelist_id, self.pricelist_reguler)

    def test_staf_sales_cannot_manage_rules(self):
        with self.assertRaises(AccessError):
            self.Rule.with_user(self.user_staf_sales).create(
                {"name": "Liar", "rule_type": "tier", "agent_tier": "reguler", "discount_percent": 50}
            )
        rule = self._proposal()
        with self.assertRaises(AccessError):
            rule.with_user(self.user_staf_sales).action_submit()

    def test_only_direktur_approves(self):
        rule = self._proposal()
        rule.action_submit()
        self.assertEqual(rule.state, "submitted")
        self.assertEqual(self._tier_percent(self.pricelist_reguler), 5)
        with self.assertRaises(AccessError):
            rule.action_approve()
        with self.assertRaises(AccessError):
            rule.write({"state": "approved"})
        rule.with_user(self.user_direktur).action_approve()
        self.assertEqual(rule.state, "approved")
        self.assertEqual(rule.approved_by_id, self.user_direktur)
        self.assertEqual(self._tier_percent(self.pricelist_reguler), 6)
        self.assertEqual(self.Rule._tier_rule("reguler"), rule)

    def test_cannot_skip_approval(self):
        rule = self._proposal()
        with self.assertRaises(UserError):
            rule.with_user(self.user_direktur).action_approve()
        with self.assertRaises(AccessError):
            self.Rule.with_user(self.user_manajer_sales).create(
                {
                    "name": "Langsung Aktif",
                    "rule_type": "tier",
                    "agent_tier": "reguler",
                    "discount_percent": 90,
                    "state": "approved",
                }
            )

    def test_rejected_rule_is_not_applied(self):
        proposal = self._proposal(discount_percent=9)
        proposal.action_submit()
        proposal.with_user(self.user_direktur).write({"rejection_reason": "Margin tipis"})
        proposal.with_user(self.user_direktur).action_reject()
        self.assertEqual(proposal.state, "rejected")
        self.assertEqual(self._tier_percent(self.pricelist_reguler), 5)

    def test_parameters_locked_after_submit(self):
        rule = self._proposal()
        rule.write({"discount_percent": 6.5})
        rule.action_submit()
        with self.assertRaises(UserError):
            rule.write({"discount_percent": 60})
        with self.assertRaises(UserError):
            rule.unlink()

    def test_promo_adds_dated_pricelist_item(self):
        promo = self._promo(discount_percent=3)
        items = promo.pricelist_item_ids
        self.assertEqual(set(items.pricelist_id.ids), {self.pricelist_reguler.id, self.pricelist_prioritas.id})
        self.assertEqual(
            sorted(items.mapped("percent_price")), [8.0, 10.0]
        )
        self.assertTrue(all(items.mapped("date_start")) and all(items.mapped("date_end")))
        self.assertEqual(self.Rule._find_rules(self.agent_reguler, self.today)[1], promo)
        later = self.today + timedelta(days=5)
        self.assertFalse(self.Rule._find_rules(self.agent_reguler, later)[1])

    def test_revision_replaces_original_on_approval(self):
        action = self.rule_reguler.with_user(self.user_manajer_sales).action_create_revision()
        revision = self.Rule.browse(action["res_id"])
        revision.with_user(self.user_manajer_sales).write({"discount_percent": 6})
        revision.with_user(self.user_manajer_sales).action_submit()
        self.assertEqual(self._tier_percent(self.pricelist_reguler), 5)
        revision.with_user(self.user_direktur).action_approve()
        self.assertFalse(self.rule_reguler.active)
        self.assertEqual(self._tier_percent(self.pricelist_reguler), 6)

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self._proposal(discount_percent=0)
        with self.assertRaises(ValidationError):
            self._proposal(rule_type="promo", agent_tier="all")
        with self.assertRaises(ValidationError):
            self._proposal(agent_tier="all")
        with self.assertRaises(ValidationError):
            self._proposal(date_start=self.today, date_end=self.today)
