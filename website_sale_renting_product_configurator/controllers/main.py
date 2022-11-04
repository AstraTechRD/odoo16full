# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale_renting.controllers.product import parse_date


class WebsiteSaleRenting(WebsiteSale):

    @http.route()
    def cart_options_update_json(self, *args, start_date=None, end_date=None, **kwargs):
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        return super().cart_options_update_json(
            *args, start_date=start_date, end_date=end_date, **kwargs
        )
