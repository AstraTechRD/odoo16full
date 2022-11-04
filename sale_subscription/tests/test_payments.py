# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch
from freezegun import freeze_time


from odoo import fields, Command
from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestSubscriptionPayments(PaymentCommon, TestSubscriptionCommon, MockEmail):

    def test_auto_payment_with_token(self):

        self.original_prepare_invoice = self.subscription._prepare_invoice

        patchers = [
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment),
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder.send_success_mail', wraps=self._mock_subscription_send_success_mail),
        ]

        for patcher in patchers:
            self.startPatcher(patcher)

        self.subscription.write({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'payment_token_id': self.payment_method.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        self.subscription._onchange_sale_order_template_id()
        self.subscription.action_confirm()
        self.mock_send_success_count = 0
        self.env['sale.order']._cron_recurring_create_invoice()
        self.assertEqual(self.mock_send_success_count, 1, 'a mail to the invoice recipient should have been sent')
        self.assertEqual(self.subscription.stage_category, 'progress', 'subscription with online payment and a payment method set should stay opened when transaction succeeds')
        invoice = self.subscription.invoice_ids.sorted('date')[-1]
        recurring_total_with_taxes = self.subscription.amount_total
        self.assertEqual(invoice.amount_total, recurring_total_with_taxes,
                         'website_subscription: the total of the recurring invoice created should be the subscription '
                         'recurring total + the products taxes')
        self.assertTrue(all(line.tax_ids.ids == self.tax_10.ids for line in invoice.invoice_line_ids),
                        'website_subscription: All lines of the recurring invoice created should have the percent tax '
                        'set on the subscription products')
        self.assertTrue(
            all(tax_line.tax_line_id == self.tax_10 for tax_line in invoice.line_ids.filtered('tax_line_id')),
            'The invoice tax lines should be set and should all use the tax set on the subscription products')

        self.mock_send_success_count = 0
        start_date = fields.Date.today() - relativedelta(months=1)
        recurring_next_date = fields.Date.today() - relativedelta(days=1)
        self.subscription.payment_token_id = False
        failing_subs = self.env['sale.order']
        subscription_mail_fail = self.subscription.copy({
            'to_renew': True,
            'date_order': start_date,
            'start_date': start_date,
            'next_invoice_date': recurring_next_date,
            'stage_id': self.subscription.stage_id.id,
            'payment_token_id': None})

        failing_subs |= subscription_mail_fail
        for dummy in range(5):
            failing_subs |= subscription_mail_fail.copy({'to_renew': True, 'stage_id': self.subscription.stage_id.id, 'is_batch': True})
        failing_subs.action_confirm()
        # issue: two problems:
        # 1) payment failed, we want to avoid trigger it twice: (double cost) --> payment_exception
        # 2) batch: we need to avoid taking subscription two time. flag remains until the end of the last trigger
        failing_subs.order_line.qty_to_invoice = 1
        self.env['sale.order']._create_recurring_invoice(automatic=True, batch_size=3)
        self.assertFalse(self.mock_send_success_count)
        failing_result = [not res for res in failing_subs.mapped('payment_exception')]
        self.assertTrue(all(failing_result), "The subscription are not flagged anymore")
        failing_result = [not res for res in failing_subs.mapped('is_batch')]
        self.assertTrue(all(failing_result), "The subscription are not flagged anymore")
        failing_subs.payment_token_id = self.payment_method.id
        # Trigger the invoicing manually after fixing it
        failing_subs._create_recurring_invoice()
        vals = [sub.payment_exception for sub in failing_subs if sub.payment_exception]
        self.assertFalse(vals, "The subscriptions are not flagged anymore, the payment succeeded")

    def test_auto_payment_across_time(self):
        self.original_prepare_invoice = self.subscription._prepare_invoice

        patchers = [
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment),
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder.send_success_mail', wraps=self._mock_subscription_send_success_mail),
        ]

        for patcher in patchers:
            self.startPatcher(patcher)

        subscription_tmpl = self.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'recurring_rule_boundary': 'limited',
            'note': "This is the template description",
            'recurring_rule_count': 4,
            'recurring_rule_type': 'month',
            'auto_close_limit': 5,
            'recurrence_id': self.recurrence_month.id
        })

        self.subscription.write({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'payment_token_id': self.payment_method.id,
            'sale_order_template_id': subscription_tmpl.id,
        })
        self.subscription._onchange_sale_order_template_id()
        self.mock_send_success_count = 0
        with freeze_time("2021-01-03"):
            self.subscription.order_line = [Command.clear()]
            self.subscription.write({
                'start_date': False,
                'next_invoice_date': False,
                'order_line': [Command.create({'product_id': self.product.id,
                                               'name': "month cheap",
                                               'price_unit': 42,
                                               'product_uom_qty': 2,
                                               }),
                               Command.create({'product_id': self.product2.id,
                                               'name': "month expensive",
                                               'price_unit': 420,
                                               'product_uom_qty': 3,
                                               }),
                               ]}
            )
            self.subscription.action_confirm()
            self.assertEqual(self.subscription.end_date, datetime.date(2021, 5, 2))
            self.env['sale.order']._cron_recurring_create_invoice()
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
            self.subscription.reconcile_pending_transaction(tx)
            # Two products are invoiced
            self.assertEqual(len(invoice.invoice_line_ids), 2, 'Two lines are invoiced')
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2021, 2, 3), 'the next invoice date should be updated')

        with freeze_time("2021-02-03"):
            self.env.invalidate_all()
            self.env['sale.order']._cron_recurring_create_invoice()
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
            self.subscription.reconcile_pending_transaction(tx)
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            self.assertEqual(invoice.date, datetime.date(2021, 2, 3), 'We invoiced today')

        with freeze_time("2021-03-03"):
            self.env.invalidate_all()
            self.env['sale.order']._cron_recurring_create_invoice()
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
            self.subscription.reconcile_pending_transaction(tx)
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            self.assertEqual(invoice.date, datetime.date(2021, 3, 3), 'We invoiced today')

        # We continue
        with freeze_time("2021-04-03"):
            self.subscription.invalidate_recordset()
            self.env['sale.order']._cron_recurring_create_invoice()
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
            self.subscription.reconcile_pending_transaction(tx)
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
            self.subscription.reconcile_pending_transaction(tx)
            self.assertEqual(invoice.date, datetime.date(2021, 4, 3), 'We invoiced today')

        with freeze_time("2022-05-03"):
            self.subscription.invalidate_recordset(fnames=['stage_id', 'stage_category'])
            self.env['sale.order'].with_context(arj=True)._cron_recurring_create_invoice()
            self.assertEqual(self.subscription.stage_category, 'closed', 'the end_date is passed, the subscription is automatically closed')
            invoice = self.subscription.invoice_ids.sorted('date')[-1]
            self.assertEqual(invoice.date, datetime.date(2021, 4, 3), 'We should not create a new invoices')

    def test_do_payment_calls_send_payment_request_only_once(self):
        self.invoice = self.env['account.move'].create(
            self.subscription._prepare_invoice()
        )
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._send_payment_request'
        ) as patched:
            self.subscription._do_payment(self._create_token(), self.invoice)
            patched.assert_called_once()

    def test_payment_token_is_saved(self):
        """Tests that the payment token is saved when a quotation is paid"""
        portal_partner = self.user_portal.partner_id
        success_payment_template_id = self.subscription_tmpl.copy()
        subscription = self.env['sale.order'].create({
            'partner_id': portal_partner.id,
            'sale_order_template_id': success_payment_template_id.id,
        })
        subscription._onchange_sale_order_template_id()
        # send quotation
        subscription.action_quotation_sent()

        test_payment_token = self.env['payment.token'].create({
            'payment_details': 'Test',
            'partner_id': portal_partner.id,
            'provider_id': self.dummy_provider.id,
            'provider_ref': 'test'
        })
        payment_with_token = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': subscription.amount_total,
            'date': subscription.date_order,
            'currency_id': subscription.currency_id.id,
            'partner_id': portal_partner.id,
            'payment_token_id': test_payment_token.id
        })

        transaction_ids = payment_with_token._create_payment_transaction()
        transaction_ids._set_done() # dummy transaction will always be successful

        subscription.write({'transaction_ids': [(6, 0, transaction_ids.ids)]})
        subscription.action_confirm()

        self.assertTrue(subscription.is_subscription)
        self.assertEqual(subscription.payment_token_id.id, test_payment_token.id)

    @mute_logger('odoo.addons.sale_subscription.models.sale_order')
    def test_exception_mail(self):
        self.subscription.write({'payment_token_id': self.payment_method.id,
                                 'client_order_ref': 'Customer REF XXXXXXX'
        })
        self.subscription.action_confirm()
        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', side_effect=Exception("Bad Token")), self.mock_mail_gateway():
            self.subscription._create_recurring_invoice(automatic=True)
        found_mail = self._find_mail_mail_wemail('accountman@test.com', 'sent', author=self.env.user.partner_id)
        mail_body = "Error during renewal of contract [%s] Customer REF XXXXXXX (Payment not recorded)" % self.subscription.id
        self.assertEqual(found_mail.body_html, mail_body)
