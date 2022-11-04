# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from .common import TestWebsiteSaleRentingCommon

@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    def test_website_sale_renting_ui(self):
        self.start_tour("/web", 'shop_buy_rental_product', login='admin')
