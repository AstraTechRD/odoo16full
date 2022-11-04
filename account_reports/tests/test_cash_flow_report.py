# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged
from odoo.tools import float_compare

@tagged('post_install', '-at_install')
class TestCashFlowReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.report = cls.env.ref('account_reports.cash_flow_report')

        cls.liquidity_journal_1 = cls.company_data['default_journal_bank']
        cls.liquidity_account = cls.liquidity_journal_1.default_account_id

        cls.receivable_account_1 = cls.company_data['default_account_receivable']
        cls.receivable_account_2 = cls.env['account.account'].create({
            'account_type': 'asset_receivable',
            'name': 'Account Receivable 2',
            'code': '121020',
            'reconcile': True,
        })
        cls.receivable_account_3 = cls.env['account.account'].create({
            'account_type': 'asset_receivable',
            'name': 'Account Receivable 3',
            'code': '121030',
            'reconcile': True,
        })

        cls.account_no_tag = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_no_tag',
            'code': '121040',
            'reconcile': True,
        })
        cls.account_financing = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_financing',
            'code': '121050',
            'reconcile': True,
            'tag_ids': cls.env.ref('account.account_tag_financing'),
        })
        cls.account_operating = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_operating',
            'code': '121060',
            'reconcile': True,
            'tag_ids': cls.env.ref('account.account_tag_operating'),
        })
        cls.account_investing = cls.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_investing',
            'code': '121070',
            'reconcile': True,
            'tag_ids': cls.env.ref('account.account_tag_investing'),
        })

    @staticmethod
    def _get_initial_expected_lines():
        return [
            ['Cash and cash equivalents, beginning of period',                       ''],
            ['Net increase in cash and cash equivalents',                            ''],
            ['Cash flows from operating activities',                                 ''],
            ['Advance Payments received from customers',                             ''],
            ['Cash received from operating activities',                              ''],
            ['Advance payments made to suppliers',                                   ''],
            ['Cash paid for operating activities',                                   ''],
            ['Cash flows from investing & extraordinary activities',                 ''],
            ['Cash in',                                                              ''],
            ['Cash out',                                                             ''],
            ['Cash flows from financing activities',                                 ''],
            ['Cash in',                                                              ''],
            ['Cash out',                                                             ''],
            ['Cash flows from unclassified activities',                              ''],
            ['Cash in',                                                              ''],
            ['Cash out',                                                             ''],
            ['Cash and cash equivalents, closing balance',                           ''],
        ]

    @classmethod
    def _update_value(cls, expected_line, value):
        if isinstance(expected_line[1], str):
            expected_line[1] = value
        elif float_compare(expected_line[1] + value, 0.0, precision_digits=cls.company_data['company'].currency_id.decimal_places) == 0:
            expected_line[1] = ''
        else:
            expected_line[1] += value

    def _reconcile_on(self, lines, account):
        lines.filtered(lambda line: line.account_id == account and not line.reconciled).reconcile()

    def assertCashFlowValues(self, report, options, expected_lines):
        folded_lines = []
        lines = report._get_lines(options)

        for line in lines:
            if line.get('style') != 'display: none;':
                folded_lines.append(line)

        self.assertLinesValues(folded_lines, [0, 1], expected_lines)

    def test_cash_flow_column_groups(self):
        self.report.filter_period_comparison = True
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-31'))
        options = self._update_comparison_filter(options, self.report, comparison_type='previous_period', number_period=1)
        options['filter_period_comparison'] = True

        invoice_current_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-08',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 1150.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 150.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice_current_period.action_post()

        payment_current_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-16',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.liquidity_account.id}),
            ],
        })
        payment_current_period.action_post()

        self._reconcile_on((invoice_current_period + payment_current_period).line_ids, self.receivable_account_1)

        invoice_previous_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-12-08',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 575.0, 'credit': 0.0,   'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,   'credit': 75.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice_previous_period.action_post()

        payment_previous_period = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2015-12-16',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 115.0, 'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 115.0, 'credit': 0.0,   'account_id': self.liquidity_account.id}),
            ],
        })
        payment_previous_period.action_post()

        self._reconcile_on((invoice_previous_period + payment_previous_period).line_ids, self.receivable_account_1)

        self.assertLinesValues(self.report._get_lines(options), [0, 1, 2], [
            ('Cash and cash equivalents, beginning of period',            115.0,         ''),
            ('Net increase in cash and cash equivalents',                 230.0,      115.0),
            ('Cash flows from operating activities',                      200.0,      100.0),
            ('Advance Payments received from customers',                     '',         ''),
            ('Cash received from operating activities',                   200.0,      100.0),
            ('Advance payments made to suppliers',                           '',         ''),
            ('Cash paid for operating activities',                           '',         ''),
            ('Cash flows from investing & extraordinary activities',         '',         ''),
            ('Cash in',                                                      '',         ''),
            ('Cash out',                                                     '',         ''),
            ('Cash flows from financing activities',                         '',         ''),
            ('Cash in',                                                      '',         ''),
            ('Cash out',                                                     '',         ''),
            ('Cash flows from unclassified activities',                    30.0,       15.0),
            ('Cash in',                                                    30.0,       15.0),
            ('Cash out',                                                     '',         ''),
            ('Cash and cash equivalents, closing balance',                345.0,      115.0),
        ])

    def test_cash_flow_multi_company_multi_currency_unfolding(self):
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))
        options['unfold_all'] = True

        account_operating_2 = self.env['account.account'].with_company(self.company_data_2['company']).create({
            'account_type': 'asset_current',
            'name': 'Account Operating',
            'code': '121160',
            'reconcile': True,
            'tag_ids': self.env.ref('account.account_tag_operating'),
        })

        invoice_with_company_2 = self.env['account.move'].with_company(self.company_data_2['company']).create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data_2['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {'debit': 1150.0, 'credit': 0.0,    'account_id': self.company_data_2['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0,    'credit': 1150.0, 'account_id': account_operating_2.id}),
            ],
        })
        invoice_with_company_2.action_post()

        payment_with_company_2 = self.env['account.move'].with_company(self.company_data_2['company']).create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data_2['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.company_data_2['default_account_receivable'].id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.company_data_2['default_journal_bank'].default_account_id.id}),
            ],
        })
        payment_with_company_2.action_post()

        self._reconcile_on((invoice_with_company_2 + payment_with_company_2).line_ids, self.company_data_2['default_account_receivable'])

        self.assertCashFlowValues(self.report, options, [
            ['Cash and cash equivalents, beginning of period',                         ''],
            ['Net increase in cash and cash equivalents',                           115.0],
            ['Cash flows from operating activities',                                115.0],
            ['Advance Payments received from customers',                               ''],
            ['Cash received from operating activities',                             115.0],
            ['121160 Account Operating',                                            115.0],
            ['Total Cash received from operating activities',                       115.0],
            ['Advance payments made to suppliers',                                     ''],
            ['Cash paid for operating activities',                                     ''],
            ['Cash flows from investing & extraordinary activities',                   ''],
            ['Cash in',                                                                ''],
            ['Cash out',                                                               ''],
            ['Cash flows from financing activities',                                   ''],
            ['Cash in',                                                                ''],
            ['Cash out',                                                               ''],
            ['Cash flows from unclassified activities',                                ''],
            ['Cash in',                                                                ''],
            ['Cash out',                                                               ''],
            ['Cash and cash equivalents, closing balance',                          115.0],
            ['101404 Bank',                                                         115.0],
            ['Total Cash and cash equivalents, closing balance',                    115.0],
        ])

    def test_cash_flow_tricky_case_1(self):
        ''' Test how the cash flow report is involved:
         - when reconciling multiple payments.
         - when dealing with multiple receivable lines.
         - when dealing with multiple partials on the same line.
         - When making an advance payment.
         - when adding entries after the report date.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))
        expected_lines = self._get_initial_expected_lines()

        # First invoice, two receivable lines on the same account.
        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 345.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 805.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,   'credit': 150.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 1000.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice.action_post()

        # First payment (20% of the invoice).
        payment_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.liquidity_account.id}),
            ],
        })
        payment_1.action_post()

        self._reconcile_on((invoice + payment_1).line_ids, self.receivable_account_1)

        self._update_value(expected_lines[1], 230.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], 200.0)   # Cash flows from operating activities
        self._update_value(expected_lines[4], 200.0)   # Cash received from operating activities
        self._update_value(expected_lines[13], 30.0)   # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 30.0)   # Cash in
        self._update_value(expected_lines[16], 230.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

        # Second payment (also 20% but will produce two partials, one on each receivable line).
        payment_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-03-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 230.0, 'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 230.0, 'credit': 0.0,   'account_id': self.liquidity_account.id}),
            ],
        })
        payment_2.action_post()

        self._reconcile_on((invoice + payment_2).line_ids, self.receivable_account_1)

        self._update_value(expected_lines[1], 230.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], 200.0)   # Cash flows from operating activities
        self._update_value(expected_lines[4], 200.0)   # Cash received from operating activities
        self._update_value(expected_lines[13], 30.0)   # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 30.0)   # Cash in
        self._update_value(expected_lines[16], 230.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

        # Third payment (residual invoice amount + 1000.0).
        payment_3 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-04-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1690.0, 'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 1690.0, 'credit': 0.0,    'account_id': self.liquidity_account.id}),
            ],
        })
        payment_3.action_post()

        self._reconcile_on((invoice + payment_3).line_ids, self.receivable_account_1)

        self._update_value(expected_lines[1], 1690.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], 1600.0)   # Cash flows from operating activities
        self._update_value(expected_lines[3], 1000.0)   # Advance Payments received from customers
        self._update_value(expected_lines[4], 600.0)    # Cash received from operating activities
        self._update_value(expected_lines[13], 90.0)    # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 90.0)    # Cash in
        self._update_value(expected_lines[16], 1690.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

        # Second invoice.
        invoice_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2018-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_operating.id}),
            ],
        })
        invoice_2.action_post()

        self._reconcile_on((invoice_2 + payment_3).line_ids, self.receivable_account_1)

        # Exceed the report date, should not affect the report.
        self.assertCashFlowValues(self.report, options, expected_lines)

        options['date']['date_to'] = '2018-01-01'

        self._update_value(expected_lines[3], -1000.0)  # Advance Payments received from customers
        self._update_value(expected_lines[4], 1000.0)  # Cash received from operating activities

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_2(self):
        ''' Test how the cash flow report is involved:
         - when dealing with multiple receivable account.
         - when making reconciliation involving multiple liquidity moves.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))
        expected_lines = self._get_initial_expected_lines()

        # First liquidity move.
        liquidity_move_1 = self.env['account.move'].create({
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 800.0, 'credit': 0.0,   'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,   'credit': 250.0, 'account_id': self.receivable_account_3.id}),
                (0, 0, {'debit': 0.0,   'credit': 250.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 300.0, 'account_id': self.liquidity_account.id}),
            ],
        })
        liquidity_move_1.action_post()

        self._update_value(expected_lines[1], -300.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], -550.0)   # Cash flows from operating activities
        self._update_value(expected_lines[3], -550.0)   # Advance Payments received from customers
        self._update_value(expected_lines[13], 250.0)   # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 250.0)   # Cash in
        self._update_value(expected_lines[16], -300.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

        # Misc. move to be reconciled at 800 / (1000 + 3000) = 20%.

        misc_move = self.env['account.move'].create({
            'date': '2016-02-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.receivable_account_1.id}),
                (0, 0, {'debit': 0.0,    'credit': 500.0,  'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 4500.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.receivable_account_2.id}),
            ],
        })
        misc_move.action_post()

        self._reconcile_on((misc_move + liquidity_move_1).line_ids, self.receivable_account_1)

        self._update_value(expected_lines[2], 3200.0)    # Cash flows from operating activities
        self._update_value(expected_lines[3], 3200.0)    # Advance Payments received from customers
        self._update_value(expected_lines[10], -3600.0)  # Cash flows from financing activities
        self._update_value(expected_lines[12], -3600.0)  # Cash out
        self._update_value(expected_lines[13], 400.0)    # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 400.0)    # Cash in

        self.assertCashFlowValues(self.report, options, expected_lines)

        # Second liquidity move.

        liquidity_move_2 = self.env['account.move'].create({
            'date': '2016-03-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 3200.0, 'credit': 0.0,    'account_id': self.receivable_account_2.id}),
                (0, 0, {'debit': 200.0,  'credit': 0.0,    'account_id': self.receivable_account_3.id}),
                (0, 0, {'debit': 0.0,    'credit': 400.0,  'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.liquidity_account.id}),
            ],
        })
        liquidity_move_2.action_post()

        self._reconcile_on((misc_move + liquidity_move_2).line_ids, self.receivable_account_2)

        self._update_value(expected_lines[1], -3000.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], -2800.0)   # Cash flows from operating activities
        self._update_value(expected_lines[3], -2800.0)   # Advance Payments received from customers
        self._update_value(expected_lines[10], -275.0)   # Cash flows from financing activities
        self._update_value(expected_lines[11], 400.0)    # Cash in
        self._update_value(expected_lines[12], -675.0)   # Cash out
        self._update_value(expected_lines[13], 75.0)     # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 75.0)     # Cash in
        self._update_value(expected_lines[16], -3000.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

        # This should not change the report.
        self._reconcile_on((liquidity_move_1 + liquidity_move_2).line_ids, self.receivable_account_3)

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_3(self):
        ''' Test how the cash flow report is involved:
         - when reconciling entries on a not-receivable/payable account.
         - when dealing with weird liquidity moves.
        '''
        expected_lines = self._get_initial_expected_lines()

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,   'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 0.0,    'credit': 500.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 500.0, 'account_id': self.account_financing.id}),
            ],
        })

        move_3 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-02-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })
        (move_1 + move_2 + move_3).action_post()

        # Reconcile everything on account_financing.
        self._reconcile_on((move_1 + move_2 + move_3).line_ids, self.account_financing)

        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))

        self._update_value(expected_lines[1], 1000.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[10], 500.0)   # Cash flows from financing activities
        self._update_value(expected_lines[11], 500.0)   # Cash in
        self._update_value(expected_lines[13], 500.0)   # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 500.0)   # Cash in
        self._update_value(expected_lines[16], 1000.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-02-01'))

        self._update_value(expected_lines[1], -500.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[10], -500.0)  # Cash flows from financing activities
        self._update_value(expected_lines[11], -500.0)  # Cash in
        self._update_value(expected_lines[16], -500.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_4(self):
        ''' The difficulty of this case is the liquidity move will pay the misc move at 1000 / 3000 = 1/3.
        However, you must take care of the sign because the 3000 in credit must become 1000 in debit.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))
        expected_lines = self._get_initial_expected_lines()

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 5000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
            ],
        })

        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids.filtered('credit') + move_2.line_ids, self.account_financing)

        self._update_value(expected_lines[1], -1000.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[13], -1000.0)  # Cash flows from unclassified activities
        self._update_value(expected_lines[15], -1000.0)  # Cash out
        self._update_value(expected_lines[16], -1000.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_5(self):
        ''' Same as test_cash_flow_tricky_case_4 in credit.'''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))
        expected_lines = self._get_initial_expected_lines()

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 3000.0, 'credit': 0.0,    'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,    'credit': 5000.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
            ],
        })

        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids.filtered('debit') + move_2.line_ids, self.account_financing)

        self._update_value(expected_lines[1], 1000.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[13], 1000.0)  # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 1000.0)  # Cash in
        self._update_value(expected_lines[16], 1000.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_6(self):
        ''' Test the additional lines on liquidity moves (e.g. bank fees) are well reported. '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))
        expected_lines = self._get_initial_expected_lines()

        moves = self.env['account.move'].create([
            {
                'date': '2016-01-01',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    (0, 0, {'debit': 3000.0, 'credit': 0.0,    'account_id': self.liquidity_account.id}),
                    (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_investing.id}),
                    (0, 0, {'debit': 0.0,    'credit': 2000.0, 'account_id': self.receivable_account_2.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,    'credit': 3000.0, 'account_id': self.liquidity_account.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_no_tag.id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.liquidity_account.id}),
                    (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.account_no_tag.id}),
                    (0, 0, {'debit': 0.0,    'credit': 2000.0, 'account_id': self.receivable_account_2.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.liquidity_account.id}),
                    (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_investing.id}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
                ],
            },
            {
                'date': '2016-01-01',
                'journal_id': self.liquidity_journal_1.id,
                'line_ids': [
                    (0, 0, {'debit': 0.0,    'credit': 4000.0, 'account_id': self.receivable_account_1.id}),
                    (0, 0, {'debit': 4000.0, 'credit': 0.0,    'account_id': self.receivable_account_2.id}),
                ],
            },
        ])

        moves.action_post()

        self._reconcile_on(moves.line_ids, self.receivable_account_1)
        self._reconcile_on(moves.line_ids, self.receivable_account_2)

        self._update_value(expected_lines[7], 2000.0)    # Cash flows from investing & extraordinary activities
        self._update_value(expected_lines[8], 2000.0)    # Cash in
        self._update_value(expected_lines[13], -2000.0)  # Cash flows from unclassified activities
        self._update_value(expected_lines[15], -2000.0)  # Cash out

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_7(self):
        ''' Test cross reconciliation between liquidity moves with additional lines when the liquidity account
        is reconcile.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))
        expected_lines = self._get_initial_expected_lines()

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 3000.0, 'credit': 0.0,    'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 0.0,    'credit': 1000.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,    'credit': 2000.0, 'account_id': self.receivable_account_2.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,    'credit': 1500.0, 'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 500.0,  'credit': 0.0,    'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 1000.0, 'credit': 0.0,    'account_id': self.receivable_account_1.id}),
            ],
        })
        (move_1 + move_2).action_post()

        self.liquidity_account.reconcile = True

        self._reconcile_on((move_1 + move_2).line_ids, self.liquidity_account)

        self._update_value(expected_lines[1], 1500.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], 1000.0 )  # Cash flows from operating activities
        self._update_value(expected_lines[3], 1000.0)   # Advance Payments received from customers
        self._update_value(expected_lines[10], 1000.0)  # Cash flows from financing activities
        self._update_value(expected_lines[11], 1000.0)  # Cash in
        self._update_value(expected_lines[13], -500.0)  # Cash flows from unclassified activities
        self._update_value(expected_lines[15], -500.0)  # Cash out
        self._update_value(expected_lines[16], 1500.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_8(self):
        ''' Difficulties on this test are:
        - The liquidity moves are reconciled to move having a total amount of 0.0.
        - Double reconciliation between the liquidity and the misc moves.
        - The reconciliations are partials.
        - There are additional lines on the misc moves.
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))
        expected_lines = self._get_initial_expected_lines()

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 100.0, 'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 900.0, 'credit': 0.0,   'account_id': self.receivable_account_2.id}),
                (0, 0, {'debit': 0.0,   'credit': 400.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 400.0, 'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_financing.id}),
            ],
        })
        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('debit'), self.account_no_tag)
        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('debit'), self.account_financing)

        self._update_value(expected_lines[1], -100.0)   # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], -900.0)   # Cash flows from operating activities
        self._update_value(expected_lines[3], -900.0)   # Advance Payments received from customers
        self._update_value(expected_lines[10], 400.0)   # Cash flows from financing activities
        self._update_value(expected_lines[11], 400.0)   # Cash in
        self._update_value(expected_lines[13], 400.0)   # Cash flows from unclassified activities
        self._update_value(expected_lines[14], 400.0)   # Cash in
        self._update_value(expected_lines[16], -100.0)  # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)

    def test_cash_flow_tricky_case_9(self):
        ''' Same as test_cash_flow_tricky_case_8 with reversed debit/credit.'''
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-01-01'))
        expected_lines = self._get_initial_expected_lines()

        move_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 100.0, 'credit': 0.0,   'account_id': self.liquidity_account.id}),
                (0, 0, {'debit': 0.0,   'credit': 900.0, 'account_id': self.receivable_account_2.id}),
                (0, 0, {'debit': 400.0, 'credit': 0.0,   'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 400.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })

        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.liquidity_journal_1.id,
            'line_ids': [
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_no_tag.id}),
                (0, 0, {'debit': 0.0,   'credit': 500.0, 'account_id': self.account_financing.id}),
                (0, 0, {'debit': 500.0, 'credit': 0.0,   'account_id': self.account_financing.id}),
            ],
        })
        (move_1 + move_2).action_post()

        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('credit'), self.account_no_tag)
        self._reconcile_on(move_1.line_ids + move_2.line_ids.filtered('credit'), self.account_financing)

        self._update_value(expected_lines[1], 100.0)    # Net increase in cash and cash equivalents
        self._update_value(expected_lines[2], 900.0)    # Cash flows from operating activities
        self._update_value(expected_lines[3], 900.0)    # Advance Payments received from customers
        self._update_value(expected_lines[10], -400.0)  # Cash flows from financing activities
        self._update_value(expected_lines[12], -400.0)  # Cash out
        self._update_value(expected_lines[13], -400.0)  # Cash flows from unclassified activities
        self._update_value(expected_lines[15], -400.0)  # Cash out
        self._update_value(expected_lines[16], 100.0)   # Cash and cash equivalents, closing balance

        self.assertCashFlowValues(self.report, options, expected_lines)
