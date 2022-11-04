# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from datetime import date
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.tests.common import new_test_user, tagged
from odoo import Command
from odoo import http


@tagged("post_install", "-at_install", "subscription_controller")
class TestSubscriptionController(PaymentHttpCommon, PaymentCommon, TestSubscriptionCommon):
    def setUp(self):
        super().setUp()
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True,}
        SaleOrder = self.env['sale.order'].with_context(context_no_mail)
        ProductTmpl = self.env['product.template'].with_context(context_no_mail)

        self.user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", tz="UTC")
        self.other_user = new_test_user(self.env, "test_user_2", email="test_user_2@nowhere.com", password="P@ssw0rd!", tz="UTC")

        self.partner = self.user.partner_id
        # Test products
        self.sub_product_tmpl = ProductTmpl.create({
            'name': 'TestProduct',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_pricing_ids': [Command.set((self.pricing_month + self.pricing_year).ids)],
        })
        self.subscription_tmpl = self.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'recurring_rule_type': 'year',
            'recurring_rule_boundary': 'limited',
            'recurring_rule_count': 2,
            'note': "This is the template description",
            'auto_close_limit': 5,
            'recurrence_id': self.recurrence_month.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "monthly",
                'product_id': self.sub_product_tmpl.product_variant_ids.id,
                'product_uom_qty': 1,
                'product_uom_id': self.sub_product_tmpl.uom_id.id
            }),
                Command.create({
                    'name': "yearly",
                    'product_id': self.sub_product_tmpl.product_variant_ids.id,
                    'product_uom_qty': 1,
                    'product_uom_id': self.sub_product_tmpl.uom_id.id,
                })
            ]

        })
        # Test Subscription
        self.subscription = SaleOrder.create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'note': "original subscription description",
            'partner_id': self.other_user.partner_id.id,
            'pricelist_id':  self.other_user.property_product_pricelist.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        self.subscription._onchange_sale_order_template_id()
        self.subscription.end_date = False  # reset the end_date
        self.subscription_tmpl.flush_recordset()
        self.subscription.flush_recordset()

    def test_renewal_identical(self):
        """ Test subscription renewal """
        with freeze_time("2021-11-18"):
            self.subscription.action_confirm()
            self.subscription.set_to_renew()
            self.assertEqual(self.subscription.end_date, date(2023, 11, 17),
                             'The end date of the subscription should be updated according to the template')
            url = "/my/subscription/%s/renew?access_token=%s" % (self.subscription.id, self.subscription.access_token)
            self.env.flush_all()
            res = self.url_open(url, allow_redirects=False)
            self.assertEqual(res.status_code, 303, "Response should redirection")
            self.env.invalidate_all()
            self.assertEqual(self.subscription.end_date, date(2025, 11, 17),
                             'The end date of the subscription should be updated according to the template')

    def test_close_contract(self):
        """ Test subscription close """
        with freeze_time("2021-11-18"):
            self.authenticate(None, None)
            self.subscription.sale_order_template_id.user_closable = True
            self.subscription.action_confirm()
            close_reason_id = self.env.ref('sale_subscription.close_reason_1')
            data = {'access_token': self.subscription.access_token, 'csrf_token': http.Request.csrf_token(self),
                    'close_reason_id': close_reason_id.id, 'closing_text': "I am broke"}
            url = "/my/subscription/%s/close" % self.subscription.id
            res = self.url_open(url, allow_redirects=False, data=data)
            self.assertEqual(res.status_code, 303)
            self.env.invalidate_all()
            self.assertEqual(self.subscription.stage_category, 'closed', 'The subscription should be closed.')
            self.assertEqual(self.subscription.end_date, date(2021, 11, 18), 'The end date of the subscription should be updated.')

    def test_prevents_assigning_not_owned_payment_tokens_to_subscriptions(self):
        malicious_user_subscription = self.env['sale.order'].create({
            'name': 'Free Subscription',
            'partner_id': self.malicious_user.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        malicious_user_subscription._onchange_sale_order_template_id()

        legit_user_subscription = self.env['sale.order'].create({
            'name': 'Free Subscription',
            'partner_id': self.legit_user.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        stolen_payment_method = self.env['payment.token'].create(
            {'payment_details': 'Jimmy McNulty',
             'partner_id': self.malicious_user.partner_id.id,
             'provider_id': self.dummy_provider.id,
             'provider_ref': 'Omar Little'})
        legit_payment_method = self.env['payment.token'].create(
            {'payment_details': 'Jimmy McNulty',
             'partner_id': self.legit_user.partner_id.id,
             'provider_id': self.dummy_provider.id,
             'provider_ref': 'Legit ref'})
        legit_user_subscription._portal_ensure_token()
        malicious_user_subscription._portal_ensure_token()
        # Payment Token exists/does not exists
        # Payment Token is accessible to user/not accessible
        # SO accessible to User/Accessible thanks to the token/Not Accessible (wrong token, no token)
        # First we check a legit token assignation for a legit subscription.
        self.authenticate('ness', 'nessnessness')
        data = {'token_id': legit_payment_method.id,
                'order_id': legit_user_subscription.id,
                'access_token': legit_user_subscription.access_token
                }
        url = self._build_url("/my/subscription/assign_token/%s" % legit_user_subscription.id)
        self._make_json_rpc_request(url, data)
        legit_user_subscription.invalidate_recordset()
        self.assertEqual(legit_user_subscription.payment_token_id, legit_payment_method)
        data = {'token_id': 9999999999999999, 'order_id': legit_user_subscription.id}
        self._make_json_rpc_request(url, data)
        legit_user_subscription.invalidate_recordset()
        self.assertEqual(legit_user_subscription.payment_token_id, legit_payment_method, "The new token should be saved on the order.")

        # Payment token is inacessible to user but the SO is OK
        self.authenticate('al', 'alalalal')
        data = {'token_id': legit_payment_method.id, 'order_id': malicious_user_subscription.id}
        url = self._build_url("/my/subscription/assign_token/%s" % malicious_user_subscription.id)
        self._make_json_rpc_request(url, data)
        malicious_user_subscription.invalidate_recordset()
        self.assertFalse(malicious_user_subscription.payment_token_id, "No token should be saved on the order.")

        # The SO is not accessible but the token is mine
        data = {'token_id': stolen_payment_method.id, 'order_id': legit_user_subscription.id}
        self._build_url("/my/subscription/assign_token/%s" % legit_user_subscription.id)
        self._make_json_rpc_request(url, data)
        legit_user_subscription.invalidate_recordset()
        self.assertEqual(legit_user_subscription.payment_token_id, legit_payment_method, "The token should not be updated")

    def test_automatic_invoice_token(self):
        # set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        self.original_prepare_invoice = self.subscription._prepare_invoice

        patchers = [
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment),
            patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder.send_success_mail', wraps=self._mock_subscription_send_success_mail),
        ]

        for patcher in patchers:
            self.startPatcher(patcher)

        subscription = self.subscription.create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'payment_token_id': self.payment_method.id,
            'sale_order_template_id': self.subscription_tmpl.id,

        })
        subscription._onchange_sale_order_template_id()
        subscription.state = 'sent'
        subscription._portal_ensure_token()
        signature = "R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=" # BASE64 of a simple image
        data = {'order_id': subscription.id, 'access_token': subscription.access_token, 'signature': signature}

        url = self._build_url("/my/orders/%s/accept" % subscription.id)
        self._make_json_rpc_request(url, data)
        data = {'order_id': subscription.id,
                'access_token': subscription.access_token,
                'amount': subscription.amount_total,
                'currency_id': subscription.currency_id.id,
                'flow': 'direct',
                'tokenization_requested': True,
                'landing_route': subscription.get_portal_url(),
                'payment_option_id': self.dummy_provider.id,
                'partner_id': subscription.partner_id.id}
        url = self._build_url("/my/orders/%s/transaction" % subscription.id)
        res = self._make_json_rpc_request(url, data)
        self.assertEqual(res.status_code, 200)
        subscription.transaction_ids.provider_id.support_manual_capture = True
        subscription.transaction_ids._set_authorized()
        subscription.transaction_ids.token_id = self.payment_method.id
        self.assertEqual(subscription.next_invoice_date, datetime.date.today())
        self.assertEqual(subscription.state, 'sale')
        subscription.transaction_ids._reconcile_after_done()  # Create the payment
        self.assertEqual(subscription.invoice_count, 1, "Only one invoice should be created")
        self.assertTrue(subscription.next_invoice_date > datetime.date.today(), "the next invoice date should be updated")
        subscription._cron_recurring_create_invoice()
        self.assertEqual(subscription.invoice_count, 1, "Only one invoice should be created")
