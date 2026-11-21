from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _kintakun_set_indonesia(self):
        indonesia = self.env.ref("base.id")
        rupiah = self.env.ref("base.IDR")
        rupiah.active = True
        for company in self.search([]):
            if company.name == "My Company":
                company.name = "Kintakun"
            self.env["stock.warehouse"].search(
                [("company_id", "=", company.id), ("name", "=", "My Company")]
            ).write({"name": "Gudang Kintakun"})
            if not company.country_id or company.country_id.code == "US":
                company.country_id = indonesia
            if company.currency_id != rupiah and not self.env["account.move.line"].search_count(
                [("company_id", "=", company.id)], limit=1
            ):
                company.currency_id = rupiah
        Pricelist = self.env["product.pricelist"].with_context(active_test=False)
        for pricelist in Pricelist.search([("currency_id", "!=", rupiah.id)]):
            company = pricelist.company_id or self.env.company
            if company.currency_id != rupiah:
                continue
            if self.env["sale.order"].search_count([("pricelist_id", "=", pricelist.id)], limit=1):
                continue
            pricelist.write(
                {
                    "currency_id": rupiah.id,
                    "name": pricelist.name.replace(pricelist.currency_id.name, rupiah.name),
                }
            )
