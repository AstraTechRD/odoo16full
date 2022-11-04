# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('-at_install', 'post_install')
class TestProjectProfitability(TestSubscriptionCommon, TestProjectProfitabilityCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.project.write({
            'partner_id': cls.user_portal.partner_id.id,
            'company_id': cls.company_data['company'].id,
            'analytic_account_id': cls.account_1.id,
        })

    def test_project_profitability(self):
        subscription = self.subscription.copy({'analytic_account_id': self.account_1.id})  # we work on a copy to test the whole flow
        self.subscription.action_cancel()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the subscription is still in draft.'
        )
        subscription.action_confirm()
        self.assertEqual(subscription.stage_id.category, 'progress')
        self.assertEqual(len(subscription.order_line), 2)
        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('subscriptions', sequence_per_invoice_type)
        subscription_sequence = sequence_per_invoice_type['subscriptions']
        self.assertTrue(subscription.sale_order_template_id, 'The subscription should have a template set.')
        self.assertEqual(subscription.sale_order_template_id.recurring_rule_boundary, 'limited')
        self.assertEqual(subscription.sale_order_template_id.recurring_rule_count, 2)
        subscription_revenues_amount_expected = subscription.recurring_monthly * subscription.sale_order_template_id.recurring_rule_count
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{'id': 'subscriptions', 'sequence': subscription_sequence, 'to_invoice': subscription_revenues_amount_expected, 'invoiced': 0.0}],
                    'total': {'to_invoice': subscription_revenues_amount_expected, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )

    def test_project_profitability_with_subscription_without_template(self):
        subscription = self.subscription.copy({'sale_order_template_id': False, 'analytic_account_id': self.account_1.id})
        self.subscription.action_cancel()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the subscription is still in draft.',
        )
        subscription.action_confirm()
        self.assertEqual(subscription.stage_id.category, 'progress')
        self.assertEqual(len(subscription.order_line), 2)
        self.assertFalse(subscription.sale_order_template_id, 'No template should be set in this subscription.')

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [{
                        'id': 'subscriptions',
                        'sequence': self.project._get_profitability_sequence_per_invoice_type()['subscriptions'],
                        'to_invoice': subscription.recurring_monthly,
                        'invoiced': 0.0,
                    }],
                    'total': {'to_invoice': subscription.recurring_monthly, 'invoiced': 0.0},
                },
                'costs': {
                    'data': [],
                    'total': {'to_bill': 0.0, 'billed': 0.0},
                }
            }
        )
