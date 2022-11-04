# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields
from odoo.tests import tagged

import json

@tagged('post_install', '-at_install')
class TestGeneralLedgerReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_1_1',     'account_id': cls.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2016_1_2',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2016_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-06-01'),
            'journal_id': cls.company_data_2['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2016_2_1',     'account_id': cls.company_data_2['default_account_payable'].id}),
                (0, 0, {'debit': 0.0,       'credit': 100.0,    'name': '2016_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'name': '2017_1_1',     'account_id': cls.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'name': '2017_1_2',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 3000.0,    'credit': 0.0,      'name': '2017_1_3',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 4000.0,    'credit': 0.0,      'name': '2017_1_4',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 5000.0,    'credit': 0.0,      'name': '2017_1_5',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 6000.0,    'credit': 0.0,      'name': '2017_1_6',     'account_id': cls.company_data['default_account_revenue'].id}),
                (0, 0, {'debit': 0.0,       'credit': 6000.0,   'name': '2017_1_7',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 7000.0,   'name': '2017_1_8',     'account_id': cls.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 8000.0,   'name': '2017_1_9',     'account_id': cls.company_data['default_account_expense'].id}),
            ],
        })
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-06-01'),
            'journal_id': cls.company_data_2['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'name': '2017_2_1',     'account_id': cls.company_data_2['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 400.0,    'name': '2017_2_2',     'account_id': cls.company_data_2['default_account_revenue'].id}),
            ],
        })
        cls.move_2017_2.action_post()

        # Archive 'default_journal_bank' to ensure archived entries are not filtered out.
        cls.company_data_2['default_journal_bank'].active = False

        # Deactive all currencies to ensure group_multi_currency is disabled.
        cls.env['res.currency'].search([('name', '!=', 'USD')]).active = False

        cls.report = cls.env.ref('account_reports.general_ledger_report')

    # -------------------------------------------------------------------------
    # TESTS: General Ledger
    # -------------------------------------------------------------------------
    def test_general_ledger_fold_unfold_multicompany_multicurrency(self):
        ''' Test unfolding a line when rendering the whole report. '''
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           1000.0,         '',             1000.0),
                ('211000 Account Payable',              100.0,          '',             100.0),
                ('211000 Account Payable',              50.0,           '',             50.0),
                ('400000 Product Sales',                20000.0,        '',             20000.0),
                ('400000 Product Sales',                '',             200.0,          -200.0),
                ('600000 Expenses',                     '',             21000.0,        -21000.0),
                ('600000 Expenses',                     200.0,          '',             200.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', '',             50.0,           -50.0),
                ('Total',                               21550.0,        21550.0,        0.0),
            ],
        )

        options['unfold_all'] = True

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           1000.0,         '',             1000.0),
                ('INV/2017/00001',                      1000.0,         '',             1000.0),
                ('Total 121000 Account Receivable',     1000.0,         '',             1000.0),
                ('211000 Account Payable',              100.0,          '',             100.0),
                ('211000 Account Payable',              50.0,           '',             50.0),
                ('400000 Product Sales',                20000.0,        '',             20000.0),
                ('INV/2017/00001',                      2000.0,         '',             2000.0),
                ('INV/2017/00001',                      3000.0,         '',             5000.0),
                ('INV/2017/00001',                      4000.0,         '',             9000.0),
                ('INV/2017/00001',                      5000.0,         '',             14000.0),
                ('INV/2017/00001',                      6000.0,         '',             20000.0),
                ('Total 400000 Product Sales',          20000.0,        '',             20000.0),
                ('400000 Product Sales',                '',             200.0,          -200.0),
                ('BNK1/2017/00001',                     '',             200.0,          -200.0),
                ('Total 400000 Product Sales',          '',             200.0,          -200.0),
                ('600000 Expenses',                     '',             21000.0,        -21000.0),
                ('INV/2017/00001',                      '',             6000.0,         -6000.0),
                ('INV/2017/00001',                      '',             7000.0,         -13000.0),
                ('INV/2017/00001',                      '',             8000.0,         -21000.0),
                ('Total 600000 Expenses',               '',             21000.0,        -21000.0),
                ('600000 Expenses',                     200.0,          '',             200.0),
                ('BNK1/2017/00001',                     200.0,          '',             200.0),
                ('Total 600000 Expenses',               200.0,          '',             200.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', '',             50.0,           -50.0),
                ('Total',                               21550.0,        21550.0,        0.0),
            ],
        )

    def test_general_ledger_multiple_years_initial_balance(self):
        # Entries in 2015 for company_1 to test the initial balance.
        move_2015_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2015-01-01'),
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 100.0,     'credit': 0.0,      'name': '2015_1_1',     'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'name': '2015_1_2',     'account_id': self.company_data['default_account_expense'].id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'name': '2015_1_3',     'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_2015_1.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           1000.0,         '',             1000.0),
                ('211000 Account Payable',              200.0,          '',             200.0),
                ('211000 Account Payable',              50.0,           '',             50.0),
                ('400000 Product Sales',                20000.0,        '',             20000.0),
                ('400000 Product Sales',                '',             200.0,          -200.0),
                ('600000 Expenses',                     '',             21000.0,        -21000.0),
                ('600000 Expenses',                     200.0,          '',             200.0),
                ('999999 Undistributed Profits/Losses', 400.0,          600.0,          -200.0),
                ('999999 Undistributed Profits/Losses', '',             50.0,           -50.0),
                ('Total',                               21850.0,        21850.0,        0.0),
            ],
        )

        options['unfold_all'] = True

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           1000.0,         '',             1000.0),
                ('INV/2017/00001',                      1000.0,         '',             1000.0),
                ('Total 121000 Account Receivable',     1000.0,         '',             1000.0),
                ('211000 Account Payable',              200.0,          '',             200.0),
                ('211000 Account Payable',              50.0,           '',             50.0),
                ('400000 Product Sales',                20000.0,        '',             20000.0),
                ('INV/2017/00001',                      2000.0,         '',             2000.0),
                ('INV/2017/00001',                      3000.0,         '',             5000.0),
                ('INV/2017/00001',                      4000.0,         '',             9000.0),
                ('INV/2017/00001',                      5000.0,         '',             14000.0),
                ('INV/2017/00001',                      6000.0,         '',             20000.0),
                ('Total 400000 Product Sales',          20000.0,        '',             20000.0),
                ('400000 Product Sales',                '',             200.0,          -200.0),
                ('BNK1/2017/00001',                     '',             200.0,          -200.0),
                ('Total 400000 Product Sales',          '',             200.0,          -200.0),
                ('600000 Expenses',                     '',             21000.0,        -21000.0),
                ('INV/2017/00001',                      '',             6000.0,         -6000.0),
                ('INV/2017/00001',                      '',             7000.0,         -13000.0),
                ('INV/2017/00001',                      '',             8000.0,         -21000.0),
                ('Total 600000 Expenses',               '',             21000.0,        -21000.0),
                ('600000 Expenses',                     200.0,          '',             200.0),
                ('BNK1/2017/00001',                     200.0,          '',             200.0),
                ('Total 600000 Expenses',               200.0,          '',             200.0),
                ('999999 Undistributed Profits/Losses', 400.0,          600.0,          -200.0),
                ('999999 Undistributed Profits/Losses', '',             50.0,           -50.0),
                ('Total',                               21850.0,        21850.0,        0.0),
            ],
        )

    def test_general_ledger_load_more(self):
        ''' Test unfolding a line to use the load more. '''
        self.env.companies = self.env.company
        self.report.load_more_limit = 2

        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [f'-account.account-{self.company_data["default_account_revenue"].id}']

        report_lines = self.report._get_lines(options)

        self.assertLinesValues(
            report_lines,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           1000.0,         '',             1000.0),
                ('211000 Account Payable',              100.0,          '',             100.0),
                ('400000 Product Sales',                20000.0,        '',             20000.0),
                ('INV/2017/00001',                      2000.0,         '',             2000.0),
                ('INV/2017/00001',                      3000.0,         '',             5000.0),
                ('Load more...',                        '',             '',             ''),
                ('Total 400000 Product Sales',          20000.0,        '',             20000.0),
                ('600000 Expenses',                     '',             21000.0,        -21000.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('Total',                               21300.0,        21300.0,        0.0),
            ],
        )

        load_more_1 = self.report._expand_unfoldable_line('_report_expand_unfoldable_line_general_ledger', report_lines[3]['id'], report_lines[6]['groupby'], options, json.loads(report_lines[6]['progress']), report_lines[6]['offset'])

        self.assertLinesValues(
            load_more_1,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('INV/2017/00001',                      4000.0,         '',             9000.0),
                ('INV/2017/00001',                      5000.0,         '',            14000.0),
                ('Load more...',                        '',             '',             ''),
            ],
        )

        load_more_2 = self.report._expand_unfoldable_line('_report_expand_unfoldable_line_general_ledger', report_lines[3]['id'], load_more_1[2]['groupby'], options, json.loads(load_more_1[2]['progress']), load_more_1[2]['offset'])

        self.assertLinesValues(
            load_more_2,
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('INV/2017/00001',                      6000.0,         '',             20000.0),
            ],
        )

    def test_general_ledger_foreign_currency_account(self):
        ''' Ensure the total in foreign currency of an account is displayed only if all journal items are sharing the
        same currency.
        '''
        self.env.user.groups_id |= self.env.ref('base.group_multi_currency')

        foreign_curr_account = self.env['account.account'].create({
            'name': 'foreign_curr_account',
            'code': 'test',
            'account_type': 'liability_current',
            'currency_id': self.currency_data['currency'].id,
            'company_id': self.company_data['company'].id,
        })

        move_2016 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'curr_1',
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 100.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'name': 'curr_2',
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -300.0,
                    'currency_id': self.currency_data['currency'].id,
                    'account_id': foreign_curr_account.id,
                }),
            ],
        })
        move_2016.action_post()

        move_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {
                    'name': 'curr_1',
                    'debit': 1000.0,
                    'credit': 0.0,
                    'amount_currency': 1000.0,
                    'currency_id': self.company_data['currency'].id,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
                (0, 0, {
                    'name': 'curr_2',
                    'debit': 0.0,
                    'credit': 1000.0,
                    'amount_currency': -2000.0,
                    'currency_id': self.currency_data['currency'].id,
                    'account_id': foreign_curr_account.id,
                }),
            ],
        })
        move_2017.action_post()
        move_2017.line_ids.flush_recordset()

        # Init options.
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfolded_lines'] = [f'-account.account-{foreign_curr_account.id}']

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Amount_currency Debit           Credit          Balance
            [   0,                                      4,              5,              6,              7],
            [
                ('121000 Account Receivable',           '',             2100.0,         '',             2100.0),
                ('211000 Account Payable',              '',             100.0,          '',             100.0),
                ('211000 Account Payable',              '',             50.0,           '',             50.0),
                ('400000 Product Sales',                '',             20000.0,        '',             20000.0),
                ('400000 Product Sales',                '',             '',             200.0,          -200.0),
                ('600000 Expenses',                     '',             '',             21000.0,        -21000.0),
                ('600000 Expenses',                     '',             200.0,          '',             200.0),
                ('999999 Undistributed Profits/Losses', '',             200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', '',             '',             50.0,           -50.0),
                ('test foreign_curr_account',           -2300.0,        '',             1100.0,         -1100.0),
                ('Initial Balance',                     -300.0,         '',             100.0,          -100.0),
                ('INV/2017/00002',                      -2000.0,        '',             1000.0,         -1100.0),
                ('Total test foreign_curr_account',     -2300.0,        '',             1100.0,         -1100.0),
                ('Total',                               '',             22650.0,        22650.0,        0.0),
            ],
            currency_map = {4: {'currency': self.currency_data['currency']}},
        )

    def test_general_ledger_filter_search_bar_print(self):
        """ Test the lines generated when a user filters on the search bar and prints the report """
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['filter_search_bar'] = '400'

        self.assertLinesValues(
            self.report.with_context(print_mode=True)._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('400000 Product Sales',                20000.0,           '',          20000.0),
                ('INV/2017/00001',                       2000.0,           '',           2000.0),
                ('INV/2017/00001',                       3000.0,           '',           5000.0),
                ('INV/2017/00001',                       4000.0,           '',           9000.0),
                ('INV/2017/00001',                       5000.0,           '',           14000.0),
                ('INV/2017/00001',                       6000.0,           '',           20000.0),
                ('Total 400000 Product Sales',          20000.0,           '',          20000.0),
                ('400000 Product Sales',                     '',        200.0,           -200.0),
                ('BNK1/2017/00001',                          '',        200.0,           -200.0),
                ('Total 400000 Product Sales',               '',        200.0,           -200.0),
                ('Total',                               20000.0,        200.0,          19800.0),
            ],
        )

        options['filter_search_bar'] = '999'

        self.assertLinesValues(
            self.report.with_context(print_mode=True)._get_lines(options),
            #   Name                                          Debit           Credit          Balance
            [   0,                                            4,              5,              6],
            [
                ('999999 Undistributed Profits/Losses',       200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses',          '',           50.0,           -50.0),
                ('Total',                                     200.0,          350.0,          -150.0),
            ],
        )

    def test_general_ledger_filter_date(self):
        move_07_2017 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-07-10'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0, 'name': '2017_1_1', 'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'name': '2017_1_2', 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })
        move_07_2017.action_post()

        # Init options
        options = self._generate_options(self.report, fields.Date.from_string('2017-07-01'), fields.Date.from_string('2017-07-31'))

        # There should not be an initial balance in account 400000 since it is an income
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      4,              5,              6],
            [
                ('121000 Account Receivable',           2000.0,         '',             2000.0),
                ('211000 Account Payable',              100.0,          '',             100.0),
                ('211000 Account Payable',              50.0,           '',             50.0),
                ('400000 Product Sales',                '',             1000.0,         -1000.0),
                ('999999 Undistributed Profits/Losses', 200.0,          300.0,          -100.0),
                ('999999 Undistributed Profits/Losses', '',             50.0,           -50.0),
                ('Total',                               2350.0,         1350.0,         1000.0),
            ],
        )
