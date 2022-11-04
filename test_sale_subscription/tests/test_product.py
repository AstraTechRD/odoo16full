# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestSubscriptionPerformance(TestSubscriptionCommon):

    def test_product_incompatibility(self):
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
        ProductTmpl = self.env['product.template'].with_context(context_no_mail)
        product = ProductTmpl.create({
            'name': 'BaseTestProduct',
            'type': 'service',
            'incompatible_checkbox': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        self.assertTrue(product.incompatible_checkbox)
        self.assertFalse(product.recurring_invoice)
        with self.assertRaises(ValidationError):
            product.write({'recurring_invoice': True})
