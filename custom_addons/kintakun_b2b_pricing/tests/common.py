from datetime import timedelta

from odoo import fields

from odoo.addons.kintakun_base.tests.common import KintakunCommon


class B2BCommon(KintakunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env["kintakun.pricing.rule"]
        cls.Rule.search([]).write({"active": False})
        cls.today = fields.Date.today()
        cls.pricelist_reguler = cls.env.ref("kintakun_b2b_pricing.pricelist_agen_reguler")
        cls.pricelist_prioritas = cls.env.ref("kintakun_b2b_pricing.pricelist_agen_prioritas")
        cls.rule_reguler = cls._approved_rule(agent_tier="reguler", discount_percent=5)
        cls.rule_prioritas = cls._approved_rule(agent_tier="prioritas", discount_percent=7)
        cls._set_stock(cls.product, 50)
        cls._set_stock(cls.product_other, 50)

    @classmethod
    def _approved_rule(cls, **values):
        vals = {
            "name": "Aturan Uji",
            "rule_type": "tier",
            "agent_tier": "reguler",
            "discount_percent": 5,
            "state": "approved",
            "approved_date": fields.Datetime.now(),
        }
        vals.update(values)
        rule = cls.env["kintakun.pricing.rule"].create(vals)
        rule._sync_pricelists()
        return rule

    @classmethod
    def _promo(cls, **values):
        vals = {
            "rule_type": "promo",
            "agent_tier": "all",
            "discount_percent": 3,
            "date_start": fields.Date.today() - timedelta(days=1),
            "date_end": fields.Date.today() + timedelta(days=1),
        }
        vals.update(values)
        return cls._approved_rule(**vals)

    @classmethod
    def _set_stock(cls, product, quantity):
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.env["stock.quant"]._update_available_quantity(product, warehouse.lot_stock_id, quantity)

    def _new_order(self, agent, quantity=10, product=None, user=None):
        user = user or self.user_staf_sales
        return (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": agent.id,
                    "order_line": [
                        (0, 0, {"product_id": (product or self.product).id, "product_uom_qty": quantity})
                    ],
                }
            )
        )

    def _confirmed_picking(self, agent=None, quantity=10):
        order = self._new_order(agent or self.agent_prioritas, quantity=quantity)
        order.action_confirm()
        picking = order.sudo().picking_ids.with_user(self.user_staf_inventory)
        return order, picking

    def _pass_check(self, picking):
        picking.action_kintakun_start_check()
        for line in picking.kintakun_check_line_ids:
            line.write({"qty_checked": line.qty_demand, "product_ok": True})
        picking.action_kintakun_finish_check()
