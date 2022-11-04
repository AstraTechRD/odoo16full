# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install', 'product_attribute')
class TestWebsiteSaleRentingProductAttributeValueConfig(TestSaleProductAttributeValueCommon):

    def test_product_attribute_value_config_get_combination_info(self):
        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()

        self.computer = self.computer.with_context(website_id=current_website.id)
        self.computer.rent_ok = True
        recurrence_hour = self.env['sale.temporal.recurrence'].sudo().create({'duration': 1, 'unit': 'hour'})
        recurrence_5_hour = self.env['sale.temporal.recurrence'].sudo().create({'duration': 1, 'unit': 'hour'})
        self.env['product.pricing'].create([
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
                'product_template_id': self.computer.id,
            }, {
                'recurrence_id': recurrence_5_hour.id,
                'price': 15.0,
                'product_template_id': self.computer.id,
            },
        ])

        # make sure the pricelist has a 10% discount
        self.env['product.pricelist.item'].create({
            'price_discount': 10,
            'compute_price': 'formula',
            'pricelist_id': pricelist.id,
        })

        discount_rate = 1 # No discount should apply on rental products (functional choice)

        currency_ratio = 2
        pricelist.currency_id = self._setup_currency(currency_ratio)

        # ensure pricelist is set to with_discount
        pricelist.discount_policy = 'with_discount'

        with MockRequest(self.env, website=current_website):
            combination_info = self.computer._get_combination_info()
            self.assertEqual(combination_info['price'], 3.5 * discount_rate * currency_ratio)
            self.assertEqual(combination_info['list_price'], 3.5 * discount_rate * currency_ratio)
            self.assertEqual(combination_info['price_extra'], 222 * currency_ratio)
            self.assertEqual(combination_info['has_discounted_price'], False)
            self.assertEqual(combination_info['current_rental_price'], 3.5 * discount_rate * currency_ratio)
            self.assertEqual(combination_info['current_rental_duration'], 1)

        with MockRequest(self.env, website=current_website):
            combination_info = self.computer.with_context(
                arj=True,
                start_date=fields.Datetime.now(),
                end_date=fields.Datetime.now() + relativedelta(hours=5)
            )._get_combination_info()
            self.assertEqual(combination_info['price'], 3.5 * discount_rate * currency_ratio)
            self.assertEqual(combination_info['list_price'], 3.5 * discount_rate * currency_ratio)
            self.assertEqual(combination_info['price_extra'], 222 * currency_ratio)
            self.assertEqual(combination_info['has_discounted_price'], False)
            self.assertEqual(combination_info['current_rental_price'], 35, "The 5h rental is equal to 5 * 3.5")
            self.assertEqual(combination_info['current_rental_duration'], 5)
