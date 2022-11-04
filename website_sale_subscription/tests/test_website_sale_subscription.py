# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from .common import TestWebsiteSaleSubscriptionCommon

@tagged('post_install', '-at_install')
class TestWebsiteSaleSubscription(TestWebsiteSaleSubscriptionCommon):

    def test_combination_info_product(self):
        self.sub_product = self.sub_product.with_context(website_id=self.current_website.id)

        with MockRequest(self.env, website=self.current_website):
            combination_info = self.sub_product._get_combination_info()
            self.assertEqual(combination_info['price'], 5)
            self.assertTrue(combination_info['is_subscription'])
            self.assertEqual(combination_info['subscription_duration'], 1)
            self.assertEqual(combination_info['subscription_unit'], 'week')

    def test_combination_info_variant_products(self):
        self.sub_with_variants.with_context(website_id=self.current_website.id)

        with MockRequest(self.env, website=self.current_website):
            combination_info = self.sub_with_variants._get_combination_info(product_id=self.sub_with_variants.product_variant_ids[0].id)
            self.assertEqual(combination_info['price'], 10)
            self.assertTrue(combination_info['is_subscription'])
            self.assertEqual(combination_info['subscription_duration'], 1)
            self.assertEqual(combination_info['subscription_unit'], 'week')

            combination_info_variant_2 = self.sub_with_variants._get_combination_info(product_id=self.sub_with_variants.product_variant_ids[-1].id)
            self.assertEqual(combination_info_variant_2['price'], 25)
            self.assertTrue(combination_info_variant_2['is_subscription'])
            self.assertEqual(combination_info_variant_2['subscription_duration'], 1)
            self.assertEqual(combination_info_variant_2['subscription_unit'], 'month')
