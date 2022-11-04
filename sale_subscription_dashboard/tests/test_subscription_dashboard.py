# -*- coding: utf-8 -*-
import datetime
import json
from freezegun import freeze_time

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSubscriptionDashboard(HttpCase):
    def setUp(self):
        super().setUp()
        TestSubscriptionDashboard._create_test_objects(self)
        mail_new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", password="P@ssw0rd!")

    @staticmethod
    def _create_test_objects(container):
        # disable most emails for speed
        context_no_mail = {"no_reset_password": True, "mail_create_nosubscribe": True, "mail_create_nolog": True}
        Subscription = container.env["sale.order"].with_context(context_no_mail)
        SubTemplate = container.env["sale.order.template"].with_context(context_no_mail)
        ProductTmpl = container.env["product.template"].with_context(context_no_mail)

        # Test product
        container.product_tmpl = ProductTmpl.create(
            {
                "name": "TestProduct",
                "type": "service",
                "recurring_invoice": True,
                "uom_id": container.env.ref("uom.product_uom_unit").id,
            }
        )
        container.product = container.product_tmpl.product_variant_id
        container.product.write(
            {
                "list_price": 50.0,
            }
        )

        # Test Subscription Template
        recurrence_month = container.recurrence_week = container.env['sale.temporal.recurrence'].create({'duration': 1, 'unit': 'month'})
        container.pricing_month = container.env['product.pricing'].create({'recurrence_id': recurrence_month.id, 'product_template_id': container.product_tmpl.id})
        container.subscription_tmpl = SubTemplate.create({
            "name": "TestSubscriptionTemplate",
            "note": "Test Subscription Template 1",
            'recurrence_id': recurrence_month.id,
            "sale_order_template_line_ids": [(0, 0, {
                'product_id': container.product.id,
                'name': 'Test monthly product',
                'product_uom_qty': 1,
                'product_uom_id': container.env.ref("uom.product_uom_unit").id,
            })],
        })
        # Test Subscription
        container.partner_id = container.env["res.partner"].create(
            {
                "name": "Beatrice Portal",
            }
        )
        container.subscription = Subscription.create(
            {
                "name": "TestSubscription",
                "is_subscription": True,
                "partner_id": container.partner_id.id,
                "pricelist_id": container.env.ref("product.list0").id,
                "sale_order_template_id": container.subscription_tmpl.id,
            }
        )

    def test_nrr(self):
        self.authenticate("test_user_1", "P@ssw0rd!")
        url = "/sale_subscription_dashboard/compute_graph_and_stats"
        res = self.url_open(
            url,
            data=json.dumps(
                {
                    "params": {
                        "stat_type": "nrr",
                        "start_date": fields.Date.to_string(fields.Date.start_of(datetime.date.today(), "month")),
                        "end_date": fields.Date.to_string(fields.Date.end_of(datetime.date.today(), "month")),
                        "filters": {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(res.status_code, 200, "Should OK")
        res_data = res.json()["result"]
        nrr_before = res_data["stats"]["value_2"]

        self.subscription.write(
            {
                "partner_id": self.partner_id.id,
                "sale_order_template_id": self.subscription_tmpl.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "TestRecurringLine",
                            "price_unit": 50,
                            "product_uom": self.product.uom_id.id,
                            "pricing_id": self.pricing_month.id
                        },
                    )
                ],
            }
        )
        self.subscription.action_confirm()
        self.subscription._create_recurring_invoice()
        invoice_id = self.subscription.invoice_ids

        res = self.url_open(
            url,
            data=json.dumps(
                {
                    "params": {
                        "stat_type": "nrr",
                        "start_date": fields.Date.to_string(fields.Date.start_of(datetime.date.today(), "month")),
                        "end_date": fields.Date.to_string(fields.Date.end_of(datetime.date.today(), "month")),
                        "filters": {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(res.status_code, 200, "Should OK")
        res_data = res.json()["result"]
        self.assertEqual(res_data["stats"]["value_2"], nrr_before, "NRR should not change after adding a subscription")

    def test_mrr(self):
        with freeze_time("2021-01-03"):
            self._test_mrr()

    def _test_mrr(self):
        start_date = fields.Date.to_string(fields.Date.start_of(datetime.date.today(), "month"))
        end_date = fields.Date.to_string(fields.Date.end_of(datetime.date.today(), "month"))
        self.subscription.write(
            {
                "partner_id": self.partner_id.id,
                "sale_order_template_id": self.subscription_tmpl.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "TestRecurringLine",
                            "product_uom": self.product.uom_id.id,
                        },
                    )
                ],
            }
        )
        self.subscription.order_line.price_unit = 50 # price_unit is computed from the pricing.price value. We override it
        self.subscription.action_confirm()
        self.subscription._create_recurring_invoice()
        invoice = self.subscription.invoice_ids
        invoice._post()

        self._check_mrr(start_date, end_date, 50)

        # make refund
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': datetime.date.today(),
            'reason': 'no reason',
            'refund_method': 'refund',
            'journal_id': invoice.journal_id.id,
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        reverse_move._post()

        self._check_mrr(start_date, end_date, 0)

    def _check_mrr(self, start_date, end_date, value):
        self.authenticate("test_user_1", "P@ssw0rd!")
        url = '/sale_subscription_dashboard/compute_stat'
        res = self.url_open(
            url,
            data=json.dumps(
                {
                    "params": {
                        "stat_type": "mrr",
                        "start_date": start_date,
                        "end_date": end_date,
                        "filters": {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.json()['result'], value)
