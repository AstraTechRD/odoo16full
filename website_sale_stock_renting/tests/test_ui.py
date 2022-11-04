# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon

@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.computer.type = 'product'
        cls.computer.allow_out_of_stock_order = False
        cls.computer.show_availability = True

        quants = cls.env['stock.quant'].create({
            'product_id': cls.computer.id,
            'inventory_quantity': 5.0,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants.action_apply_inventory()

    def test_website_sale_stock_renting_ui(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/web", 'shop_buy_rental_stock_product', login='admin')
