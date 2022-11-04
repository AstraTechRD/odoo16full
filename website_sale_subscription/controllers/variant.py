# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleRentingVariantController(WebsiteSaleVariantController):

    @http.route()
    def get_combination_info_website(self, *args, **kwargs):
        res = super(WebsiteSaleRentingVariantController, self).get_combination_info_website(*args, **kwargs)
        res['is_combination_possible'] = res.get('is_combination_possible', True) and res.get('is_recurrence_possible', True)
        return res
