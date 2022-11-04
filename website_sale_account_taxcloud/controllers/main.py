# -*- coding: utf-8 -*-

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.website_sale.controllers import main

class WebsiteSale(main.WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        res = {}
        res['on_payment_step'] = True

        if order.fiscal_position_id.is_taxcloud:
            try:
                order.validate_taxes_on_sales_order()
            except ValidationError:
                res['errors'].append((_("Validation Error"), _("This address does not appear to be valid. Please make sure it has been filled in correctly.")))

        res.update(super(WebsiteSale, self)._get_shop_payment_values(order, **kwargs))
        return res
