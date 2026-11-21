from . import models
from . import wizard


def post_init_hook(env):
    env["res.partner"].search([("is_kintakun_agent", "=", True)])._kintakun_assign_pricelist()
    companies = env["res.company"].search([])
    if "stock_move_sms_validation" in companies._fields:
        companies.write({"stock_move_sms_validation": False})
