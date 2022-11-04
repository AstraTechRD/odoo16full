# -*- coding: utf-8 -*-
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestBankRecWidget(TestBankRecWidgetCommon, HttpCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env['account.reconcile.model']\
            .search([('company_id', '=', cls.company_data['company'].id)])\
            .write({'past_months_limit': None})

    def test_tour_bank_rec_widget(self):
        st_line1 = self._create_st_line(1000.0, payment_ref="line1", sequence=1)
        st_line2 = self._create_st_line(1000.0, payment_ref="line2", sequence=2)
        self._create_st_line(1000.0, payment_ref="line3", sequence=3)

        # INV/2019/00001:
        self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a,
            invoice_date='2019-01-01',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )

        # INV/2019/00002:
        self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a,
            invoice_date='2019-01-01',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )

        self.start_tour('/web', 'account_accountant_bank_rec_widget', login=self.env.user.login)

        self.assertRecordValues(st_line1.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line1.journal_id.default_account_id.id,           'balance': 1000.0,  'reconciled': False},
            {'account_id': self.company_data['default_account_receivable'].id,  'balance': -1000.0, 'reconciled': True},
        ])

        tax_account = self.company_data['default_tax_sale'].invoice_repartition_line_ids.account_id
        self.assertRecordValues(st_line2.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line2.journal_id.default_account_id.id,           'balance': 1000.0,  'tax_ids': []},
            {'account_id': self.company_data['default_account_payable'].id,     'balance': -869.57, 'tax_ids': self.company_data['default_tax_sale'].ids},
            {'account_id': tax_account.id,                                      'balance': -130.43, 'tax_ids': []},
        ])
