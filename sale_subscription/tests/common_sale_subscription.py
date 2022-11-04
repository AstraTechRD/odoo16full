# -*- coding: utf-8 -*-

import datetime

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged
from odoo import Command


class TestSubscriptionCommon(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # disable most emails for speed
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
        AnalyticPlan = cls.env['account.analytic.plan'].with_context(context_no_mail)
        Analytic = cls.env['account.analytic.account'].with_context(context_no_mail)
        SaleOrder = cls.env['sale.order'].with_context(context_no_mail)
        Tax = cls.env['account.tax'].with_context(context_no_mail)
        ProductTmpl = cls.env['product.template'].with_context(context_no_mail)
        cls.country_belgium = cls.env.ref('base.be')

        # Minimal CoA & taxes setup
        cls.account_payable = cls.company_data['default_account_payable']
        cls.account_receivable = cls.company_data['default_account_receivable']
        cls.account_income = cls.company_data['default_account_revenue']

        cls.tax_10 = Tax.create({
            'name': "10% tax",
            'amount_type': 'percent',
            'amount': 10,
        })
        cls.tax_20 = Tax.create({
            'name': "20% tax",
            'amount_type': 'percent',
            'amount': 20,
        })
        cls.journal = cls.company_data['default_journal_sale']

        # Test products
        cls.recurrence_week = cls.env['sale.temporal.recurrence'].create({'duration': 1, 'unit': 'week'})
        cls.recurrence_month = cls.env['sale.temporal.recurrence'].create({'duration': 1, 'unit': 'month'})
        cls.recurrence_year = cls.env['sale.temporal.recurrence'].create({'duration': 1, 'unit': 'year'})
        cls.recurrence_2_month = cls.env['sale.temporal.recurrence'].create({'duration': 2, 'unit': 'month'})

        cls.pricing_month = cls.env['product.pricing'].create({'recurrence_id': cls.recurrence_month.id})
        cls.pricing_year = cls.env['product.pricing'].create({'recurrence_id': cls.recurrence_year.id, 'price': 100})
        cls.pricing_year_2 = cls.env['product.pricing'].create({'recurrence_id': cls.recurrence_year.id, 'price': 200})
        cls.pricing_year_3 = cls.env['product.pricing'].create({'recurrence_id': cls.recurrence_year.id, 'price': 300})
        cls.sub_product_tmpl = ProductTmpl.create({
            'name': 'BaseTestProduct',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'product_pricing_ids': [(6, 0, (cls.pricing_month | cls.pricing_year).ids)]
        })
        cls.product = cls.sub_product_tmpl.product_variant_id
        cls.product.write({
            'list_price': 50.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })

        cls.product_tmpl_2 = ProductTmpl.create({
            'name': 'TestProduct2',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product2 = cls.product_tmpl_2.product_variant_id
        cls.product2.write({
            'list_price': 20.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })

        cls.product_tmpl_3 = ProductTmpl.create({
            'name': 'TestProduct3',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product3 = cls.product_tmpl_3.product_variant_id
        cls.product3.write({
            'list_price': 15.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })

        cls.product_tmpl_4 = ProductTmpl.create({
            'name': 'TestProduct4',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product4 = cls.product_tmpl_4.product_variant_id
        cls.product4.write({
            'list_price': 15.0,
            'taxes_id': [(6, 0, [cls.tax_20.id])],
            'property_account_income_id': cls.account_income.id,
        })
        cls.product_tmpl_5 = ProductTmpl.create({
            'name': 'One shot product',
            'type': 'service',
            'recurring_invoice': False,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
        })
        cls.product5 = cls.product_tmpl_3.product_variant_id
        cls.product5.write({
            'list_price': 42.0,
            'taxes_id': [(6, 0, [cls.tax_10.id])],
            'property_account_income_id': cls.account_income.id,
        })
        cls.subscription_tmpl = cls.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'recurring_rule_type': 'year',
            'recurring_rule_boundary': 'limited',
            'recurring_rule_count': 2,
            'note': "This is the template description",
            'auto_close_limit': 5,
            'recurrence_id': cls.recurrence_month.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "Product 1",
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'product_uom_id': cls.product.uom_id.id
            }),
                Command.create({
                    'name': "Product 2",
                    'product_id': cls.product2.id,
                    'product_uom_qty': 1,
                    'product_uom_id': cls.product2.uom_id.id,
                })
            ]
        })
        # Test user
        TestUsersEnv = cls.env['res.users'].with_context({'no_reset_password': True})
        group_portal_id = cls.env.ref('base.group_portal').id
        cls.country_belgium = cls.env.ref('base.be')
        cls.user_portal = TestUsersEnv.create({
            'name': 'Beatrice Portal',
            'login': 'Beatrice',
            'country_id': cls.country_belgium.id,
            'email': 'beatrice.employee@example.com',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
            'company_id': cls.company_data['company'].id,
        })

        cls.malicious_user = TestUsersEnv.create({
            'name': 'Al Capone',
            'login': 'al',
            'password': 'alalalal',
            'email': 'al@capone.it',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_receivable_id': cls.account_receivable.id,
            'property_account_payable_id': cls.account_receivable.id,
        })
        cls.legit_user = TestUsersEnv.create({
            'name': 'Eliot Ness',
            'login': 'ness',
            'password': 'nessnessness',
            'email': 'ness@USDT.us',
            'groups_id': [(6, 0, [group_portal_id])],
            'property_account_receivable_id': cls.account_receivable.id,
            'property_account_payable_id': cls.account_receivable.id,
        })

        # Test analytic account
        cls.plan_1 = AnalyticPlan.create({
            'name': 'Test Plan 1',
            'company_id': False,
        })
        cls.account_1 = Analytic.create({
            'partner_id': cls.user_portal.partner_id.id,
            'name': 'Test Account 1',
            'plan_id': cls.plan_1.id,
        })
        cls.account_2 = Analytic.create({
            'partner_id': cls.user_portal.partner_id.id,
            'name': 'Test Account 2',
            'plan_id': cls.plan_1.id,
        })

        # Test Subscription
        cls.subscription = SaleOrder.create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'recurrence_id': cls.recurrence_month.id,
            'note': "original subscription description",
            'partner_id': cls.user_portal.partner_id.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'sale_order_template_id': cls.subscription_tmpl.id,
        })
        cls.subscription._onchange_sale_order_template_id()
        cls.subscription.start_date = False # the confirmation will set the start_date
        cls.subscription.end_date = False # reset the end_date too
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref('base.us')
        cls.account_receivable = cls.env['account.account'].create(
            {'name': 'Ian Anderson',
             'code': 'IA',
             'account_type': 'asset_receivable',
             'company_id': cls.company.id,
             'reconcile': True})
        cls.account_sale = cls.env['account.account'].create(
            {'name': 'Product Sales ',
             'code': 'S200000',
             'account_type': 'income',
             'company_id': cls.company.id,
             'reconcile': False})

        cls.sale_journal = cls.env['account.journal'].create(
            {'name': 'reflets.info',
             'code': 'ref',
             'type': 'sale',
             'company_id': cls.company.id,
             'default_account_id': cls.account_sale.id})
        belgium = cls.env.ref('base.be')
        cls.partner = cls.env['res.partner'].create(
            {'name': 'Stevie Nicks',
             'email': 'sti@fleetwood.mac',
             'country_id': belgium.id,
             'property_account_receivable_id': cls.account_receivable.id,
             'property_account_payable_id': cls.account_receivable.id,
             'company_id': cls.company.id})
        cls.provider = cls.env['payment.provider'].create(
            {'name': 'The Wire',
             'company_id': cls.company.id,
             'state': 'test',
             'redirect_form_view_id': cls.env['ir.ui.view'].search([('type', '=', 'qweb')], limit=1).id})
        cls.payment_method = cls.env['payment.token'].create(
            {'payment_details': 'Jimmy McNulty',
             'partner_id': cls.partner.id,
             'provider_id': cls.provider.id,
             'provider_ref': 'Omar Little'})
        Partner = cls.env['res.partner']
        cls.partner_a_invoice = Partner.create({
            'parent_id': cls.partner_a.id,
            'type': 'invoice',
        })
        cls.partner_a_shipping = Partner.create({
            'parent_id': cls.partner_a.id,
            'type': 'delivery',
        })
        cls.mock_send_success_count = 0

    # Mocking for 'test_auto_payment_with_token'
    # Necessary to have a valid and done transaction when the cron on subscription passes through
    def _mock_subscription_do_payment(self, payment_method, invoice):
        tx_obj = self.env['payment.transaction']
        reference = "CONTRACT-%s-%s" % (self.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S%f'))
        values = {
            'amount': invoice.amount_total,
            'provider_id': self.provider.id,
            'operation': 'offline',
            'currency_id': invoice.currency_id.id,
            'reference': reference,
            'token_id': payment_method.id,
            'partner_id': invoice.partner_id.id,
            'partner_country_id': invoice.partner_id.country_id.id,
            'invoice_ids': [(6, 0, [invoice.id])],
            'state': 'done',
        }
        tx = tx_obj.create(values)
        return tx

    # Mocking for 'test_auto_payment_with_token'
    # Otherwise the whole sending mail process will be triggered
    # And we are not here to test that flow, and it is a heavy one
    def _mock_subscription_send_success_mail(self, tx, invoice):
        self.mock_send_success_count += 1
        return 666

    # Mocking for 'test_auto_payment_with_token'
    # Avoid account_id is False when creating the invoice
    def _mock_prepare_invoice_data(self):
        invoice = self.original_prepare_invoice()
        invoice['partner_bank_id'] = False
        return invoice

    def flush_tracking(self):
        self.env.flush_all()
        self.cr.flush()
