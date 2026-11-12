from odoo.tests.common import TransactionCase


class KintakunCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        Region = cls.env["kintakun.region"]
        cls.region_bandung = Region.create({"name": "Uji Bandung", "code": "T-BDG"})
        cls.region_jakarta = Region.create({"name": "Uji Jakarta", "code": "T-JKT"})

        cls.user_staf_sales = cls._new_user("t_staf_sales", "group_staf_sales")
        cls.user_manajer_sales = cls._new_user("t_manajer_sales", "group_manajer_sales")
        cls.user_staf_inventory = cls._new_user("t_staf_inventory", "group_staf_inventory")
        cls.user_manajer_procurement = cls._new_user(
            "t_manajer_procurement", "group_manajer_procurement"
        )
        cls.user_manajer_it = cls._new_user("t_manajer_it", "group_manajer_it")
        cls.user_manajer_finance = cls._new_user("t_manajer_finance", "group_manajer_finance")
        cls.user_direktur = cls._new_user("t_direktur", "group_direktur")

        cls.agent_reguler = cls._new_agent("Agen Uji Reguler", "reguler", cls.region_bandung)
        cls.agent_prioritas = cls._new_agent(
            "Agen Uji Prioritas", "prioritas", cls.region_jakarta
        )
        cls.product = cls._new_product("Sprei Uji Bunga 160x200", "Bunga", "T-BNG-160")
        cls.product_other = cls._new_product("Sprei Uji Geometri 160x200", "Geometri", "T-GEO-160")

    @classmethod
    def _new_user(cls, login, group):
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@kintakun.example",
                "groups_id": [(6, 0, [cls.env.ref(f"kintakun_base.{group}").id])],
            }
        )

    @classmethod
    def _new_agent(cls, name, tier, region):
        return cls.env["res.partner"].create(
            {
                "name": name,
                "is_company": True,
                "is_kintakun_agent": True,
                "agent_tier": tier,
                "agent_region_id": region.id,
            }
        )

    @classmethod
    def _new_product(cls, name, motif, barcode):
        return cls.env["product.product"].create(
            {
                "name": name,
                "detailed_type": "product",
                "invoice_policy": "delivery",
                "list_price": 100000,
                "taxes_id": [(5, 0, 0)],
                "barcode": barcode,
                "kintakun_motif": motif,
                "kintakun_size": "160x200",
            }
        )
