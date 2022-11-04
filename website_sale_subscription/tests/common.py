# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon

class TestWebsiteSaleSubscriptionCommon(TestSubscriptionCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Subscription Company',
        })

        cls.current_website = cls.env['website'].get_current_website()

        ProductTemplate = cls.env['product.template']
        ProductAttributeVal = cls.env['product.attribute.value']
        Pricing = cls.env['product.pricing']

        # create product 1
        cls.sub_product = ProductTemplate.create({
            'name': 'Streaming SUB Weekly',
            'list_price': 0,
            'recurring_invoice': True,
        })
        Pricing.create([
            {
                'recurrence_id': cls.recurrence_week.id,
                'price': 5.0,
                'product_template_id': cls.sub_product.id,
            }
        ])

        cls.sub_product_2 = ProductTemplate.create({
            'name': 'Streaming SUB Monthly',
            'list_price': 0,
            'recurring_invoice': True,
        })
        Pricing.create([
            {
                'recurrence_id': cls.recurrence_month.id,
                'price': 25.0,
                'product_template_id': cls.sub_product_2.id,
            }
        ])

        # create product with variants
        product_attribute = cls.env['product.attribute'].create({'name': 'Color'})
        product_attribute_val1 = ProductAttributeVal.create({
            'name': 'Black',
            'attribute_id': product_attribute.id
        })
        product_attribute_val2 = ProductAttributeVal.create({
            'name': 'White',
            'attribute_id': product_attribute.id
        })

        cls.sub_with_variants = ProductTemplate.create({
            'recurring_invoice': True,
            'detailed_type': 'service',
            'name': 'Variant Products',
        })

        cls.sub_with_variants.attribute_line_ids = [(Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': [Command.set([product_attribute_val1.id, product_attribute_val2.id])],
        }))]

        pricing1 = Pricing.create({
            'recurrence_id': cls.recurrence_week.id,
            'price': 10,
            'product_template_id': cls.sub_with_variants.id,
            'product_variant_ids': [Command.link(cls.sub_with_variants.product_variant_ids[0].id)],
        })

        pricing2 = Pricing.create({
            'recurrence_id': cls.recurrence_month.id,
            'price': 25,
            'product_template_id': cls.sub_with_variants.id,
            'product_variant_ids': [Command.link(cls.sub_with_variants.product_variant_ids[-1].id)],
        })

        cls.sub_with_variants.write({
            'product_pricing_ids': [Command.set([pricing1.id, pricing2.id])]
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'partner_a',
        })
