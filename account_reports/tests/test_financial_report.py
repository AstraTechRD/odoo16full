# -*- coding: utf-8 -*-
# pylint: disable=C0326

from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestFinancialReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # ==== Partners ====

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False})
        cls.partner_c = cls.env['res.partner'].create({'name': 'partner_c', 'company_id': False})

        # ==== Accounts ====

        # Cleanup existing "Current year earnings" accounts since we can only have one by company.
        cls.env['account.account'].search([
            ('company_id', 'in', (cls.company_data['company'] + cls.company_data_2['company']).ids),
            ('account_type', '=', 'equity_unaffected'),
        ]).unlink()

        account_type_data = [
            ('asset_receivable',    {'reconcile': True}),
            ('liability_payable',   {'reconcile': True}),
            ('asset_cash',          {}),
            ('asset_current',       {}),
            ('asset_prepayments',   {}),
            ('asset_fixed',         {}),
            ('asset_non_current',   {}),
            ('equity',              {}),
            ('equity_unaffected',   {}),
            ('income',              {}),
        ]

        accounts = cls.env['account.account'].create([{
            **data[1],
            'name': 'account%s' % i,
            'code': 'code%s' % i,
            'account_type': data[0],
            'company_id': cls.company_data['company'].id,
        } for i, data in enumerate(account_type_data)])

        accounts_2 = cls.env['account.account'].create([{
            **data[1],
            'name': 'account%s' % (i + 100),
            'code': 'code%s' % (i + 100),
            'account_type': data[0],
            'company_id': cls.company_data_2['company'].id,
        } for i, data in enumerate(account_type_data)])

        # ==== Custom filters ====

        cls.horizontal_group = cls.env['account.report.horizontal.group'].create({
            'name': 'Horizontal Group',
            'rule_ids': [
                Command.create({
                    'field_name': 'partner_id',
                    'domain': f"[('id', 'in', {(cls.partner_a + cls.partner_b).ids})]",
                }),
                Command.create({
                    'field_name': 'account_id',
                    'domain': f"[('id', 'in', {accounts[:2].ids})]",
                }),
            ],
        })

        # ==== Journal entries ====

        cls.move_2019 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2019-01-01'),
            'line_ids': [
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': accounts[1].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'account_id': accounts[2].id,   'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'account_id': accounts[3].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 1100.0,   'account_id': accounts[4].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 700.0,     'credit': 0.0,      'account_id': accounts[6].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 800.0,    'account_id': accounts[7].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 800.0,     'credit': 0.0,      'account_id': accounts[8].id,   'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2019.action_post()

        cls.move_2018 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2018-01-01'),
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 1000.0,   'account_id': accounts[2].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 250.0,     'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 250.0,    'account_id': accounts[9].id,   'partner_id': cls.partner_a.id}),
            ],
        })
        cls.move_2018.action_post()

        cls.move_2017 = cls.env['account.move'].with_company(cls.company_data_2['company']).create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'line_ids': [
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'account_id': accounts_2[0].id, 'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 4000.0,   'account_id': accounts_2[2].id, 'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 5000.0,   'account_id': accounts_2[4].id, 'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 7000.0,    'credit': 0.0,      'account_id': accounts_2[6].id, 'partner_id': cls.partner_a.id}),
            ],
        })
        cls.move_2017.action_post()

        cls.report = cls.env.ref('account_reports.balance_sheet')

        cls.report_no_parent_id = cls.env["account.report"].create({
            'name': "Test report",

            'column_ids': [
                Command.create({
                    'name': 'Balance',
                    'expression_label': 'balance',
                    'sequence': 1
                })
            ],

            'line_ids': [
                Command.create({
                    'name': "Invisible Partner A line",
                    'code': "INVA",
                    'sequence': 1,
                    'hierarchy_level': 0,
                    'groupby': "account_id",
                    'foldable': True,
                    'expression_ids': [Command.clear(), Command.create({
                        'label': 'balance',
                        'engine': 'domain',
                        'formula': [("partner_id", "=", cls.partner_a.id)],
                        'subformula': 'sum',
                        'date_scope': 'strict_range'
                    })],
                }),
                Command.create({
                    'name': "Invisible Partner B line",
                    'code': "INVB",
                    'sequence': 2,
                    'hierarchy_level': 0,
                    'groupby': "account_id",
                    'foldable': True,
                    'expression_ids': [Command.clear(), Command.create({
                        'label': 'balance',
                        'engine': 'domain',
                        'formula': [("partner_id", "=", cls.partner_b.id)],
                        'subformula': 'sum',
                        'date_scope': 'strict_range'
                    })],
                }),
                Command.create({
                    'name': "Total of Invisible lines",
                    'code': "INVT",
                    'sequence': 3,
                    'hierarchy_level': 0,
                    'expression_ids': [Command.clear(), Command.create({
                        'label': 'balance',
                        'engine': 'aggregation',
                        'formula': 'INVA.balance + INVB.balance',
                        'date_scope': 'normal'
                    })],
                }),
            ],
        })

    def _build_generic_id_from_financial_line(self, financial_rep_ln_xmlid):
        report_line = self.env.ref(financial_rep_ln_xmlid)
        return '-account.financial.html.report.line-%s' % report_line.id

    def _get_line_id_from_generic_id(self, generic_id):
        return int(generic_id.split('-')[-1])

    def test_financial_report_strict_range_on_report_lines_with_no_parent_id(self):
        """ Tests that lines with no parent can be correctly filtered by date range """
        options = self._generate_options(self.report_no_parent_id, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options.pop('multi_company', None)

        lines = self.report_no_parent_id._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                         Balance
            [   0,                           1],
            [
                ('Invisible Partner A line', 1150.0),
                ('Invisible Partner B line', -1675.0),
                ('Total of Invisible lines', -525.0),
            ])

    def test_financial_report_strict_empty_range_on_report_lines_with_no_parent_id(self):
        """ Tests that lines with no parent can be correctly filtered by date range with no invoices"""
        options = self._generate_options(self.report_no_parent_id, fields.Date.from_string('2019-03-01'), fields.Date.from_string('2019-03-31'))
        options.pop('multi_company', None)

        lines = self.report_no_parent_id._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                          Balance
            [   0,                            1],
            [
                ('Invisible Partner A line',  ''),
                ('Invisible Partner B line',  ''),
                ('Total of Invisible lines',  ''),
            ])

    @freeze_time("2016-06-06")
    def test_balance_sheet_today_current_year_earnings(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2016-02-02',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 110,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2016-06-01'), fields.Date.from_string('2016-06-06'))
        options['date']['filter'] = 'today'
        options.pop('multi_company', None)

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      110.0),
                ('Current Assets',                              110.0),
                ('Bank and Cash Accounts',                         ''),
                ('Receivables',                                 110.0),
                ('Current Assets',                                 ''),
                ('Prepayments',                                    ''),
                ('Total Current Assets',                        110.0),
                ('Plus Fixed Assets',                              ''),
                ('Plus Non-current Assets',                        ''),
                ('Total ASSETS',                                110.0),

                ('LIABILITIES',                                    ''),
                ('Current Liabilities',                            ''),
                ('Current Liabilities',                            ''),
                ('Payables',                                       ''),
                ('Total Current Liabilities',                      ''),
                ('Plus Non-current Liabilities',                   ''),
                ('Total LIABILITIES',                              ''),

                ('EQUITY',                                      110.0),
                ('Unallocated Earnings',                        110.0),
                ('Current Year Unallocated Earnings',           110.0),
                ('Current Year Earnings',                       110.0),
                ('Current Year Allocated Earnings',                ''),
                ('Total Current Year Unallocated Earnings',     110.0),
                ('Previous Years Unallocated Earnings',            ''),
                ('Total Unallocated Earnings',                  110.0),
                ('Retained Earnings',                              ''),
                ('Total EQUITY',                                110.0),

                ('LIABILITIES + EQUITY',                        110.0),
            ],
        )

    @freeze_time("2016-05-05")
    def test_balance_sheet_last_month_vs_custom_current_year_earnings(self):
        """
        Checks the balance sheet calls the right period of the P&L when using last_month date filter, or an equivalent custom filter
        (this used to fail due to options regeneration made by the P&L's _get_options())"
        """
        to_invoice = [('15', '11'), ('15', '12'), ('16', '01'), ('16', '02'), ('16', '03'), ('16', '04')]
        for year, month in to_invoice:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': f'20{year}-{month}-01',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000,
                    'tax_ids': [],
                })]
            })
            invoice.action_post()
        expected_result =[
                ('ASSETS',                                      6000.0),
                ('Current Assets',                              6000.0),
                ('Bank and Cash Accounts',                      ''),
                ('Receivables',                                 6000.0),
                ('Current Assets',                              ''),
                ('Prepayments',                                 ''),
                ('Total Current Assets',                        6000.0),
                ('Plus Fixed Assets',                           ''),
                ('Plus Non-current Assets',                     ''),
                ('Total ASSETS',                                6000.0),

                ('LIABILITIES',                                 ''),
                ('Current Liabilities',                         ''),
                ('Current Liabilities',                         ''),
                ('Payables',                                    ''),
                ('Total Current Liabilities',                   ''),
                ('Plus Non-current Liabilities',                ''),
                ('Total LIABILITIES',                           ''),

                ('EQUITY',                                      6000.0),
                ('Unallocated Earnings',                        6000.0),
                ('Current Year Unallocated Earnings',           4000.0),
                ('Current Year Earnings',                       4000.0),
                ('Current Year Allocated Earnings',             ''),
                ('Total Current Year Unallocated Earnings',     4000.0),
                ('Previous Years Unallocated Earnings',         2000.0),
                ('Total Unallocated Earnings',                  6000.0),
                ('Retained Earnings',                           ''),
                ('Total EQUITY',                                6000.0),
                ('LIABILITIES + EQUITY',                        6000.0),

            ]
        options = self._generate_options(self.report, fields.Date.from_string('2016-05-05'), fields.Date.from_string('2016-05-05'))
        options.pop('multi_company', None)

        # End of Last Month
        options['date']['filter'] = 'last_month'
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            expected_result,
        )
        # Custom
        options['date']['filter'] = 'custom'
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            expected_result,
        )

    def test_financial_report_single_company(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfolded_lines'] = [line_id]
        options.pop('multi_company', None)

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                        50.0),
                ('Current Assets',                              -650.0),
                ('Bank and Cash Accounts',                     -1300.0),
                ('code2 account2',                             -1300.0),
                ('Total Bank and Cash Accounts',               -1300.0),
                ('Receivables',                                 1350.0),
                ('Current Assets',                               400.0),
                ('Prepayments',                                -1100.0),
                ('Total Current Assets',                        -650.0),
                ('Plus Fixed Assets',                               ''),
                ('Plus Non-current Assets',                      700.0),
                ('Total ASSETS',                                  50.0),

                ('LIABILITIES',                                 -200.0),
                ('Current Liabilities',                         -200.0),
                ('Current Liabilities',                             ''),
                ('Payables',                                    -200.0),
                ('Total Current Liabilities',                   -200.0),
                ('Plus Non-current Liabilities',                    ''),
                ('Total LIABILITIES',                           -200.0),

                ('EQUITY',                                       250.0),
                ('Unallocated Earnings',                        -550.0),
                ('Current Year Unallocated Earnings',           -800.0),
                ('Current Year Earnings',                           ''),
                ('Current Year Allocated Earnings',             -800.0),
                ('Total Current Year Unallocated Earnings',     -800.0),
                ('Previous Years Unallocated Earnings',          250.0),
                ('Total Unallocated Earnings',                  -550.0),
                ('Retained Earnings',                            800.0),
                ('Total EQUITY',                                 250.0),

                ('LIABILITIES + EQUITY',                          50.0),
            ],
        )

        unfolded_lines = self.report._get_unfolded_lines(lines, line_id)
        self.assertLinesValues(
            unfolded_lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Bank and Cash Accounts',                      -1300.0),
                ('code2 account2',                              -1300.0),
                ('Total Bank and Cash Accounts',                -1300.0),
            ],
        )

    def test_financial_report_multi_company_currency(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfolded_lines'] = [line_id]

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                        50.0),
                ('Current Assets',                             -4150.0),
                ('Bank and Cash Accounts',                     -3300.0),
                ('code102 account102',                         -2000.0),
                ('code2 account2',                             -1300.0),
                ('Total Bank and Cash Accounts',               -3300.0),
                ('Receivables',                                 2350.0),
                ('Current Assets',                               400.0),
                ('Prepayments',                                -3600.0),
                ('Total Current Assets',                       -4150.0),
                ('Plus Fixed Assets',                               ''),
                ('Plus Non-current Assets',                     4200.0),
                ('Total ASSETS',                                  50.0),

                ('LIABILITIES',                                 -200.0),
                ('Current Liabilities',                         -200.0),
                ('Current Liabilities',                             ''),
                ('Payables',                                    -200.0),
                ('Total Current Liabilities',                   -200.0),
                ('Plus Non-current Liabilities',                    ''),
                ('Total LIABILITIES',                           -200.0),

                ('EQUITY',                                       250.0),
                ('Unallocated Earnings',                        -550.0),
                ('Current Year Unallocated Earnings',           -800.0),
                ('Current Year Earnings',                           ''),
                ('Current Year Allocated Earnings',             -800.0),
                ('Total Current Year Unallocated Earnings',     -800.0),
                ('Previous Years Unallocated Earnings',          250.0),
                ('Total Unallocated Earnings',                  -550.0),
                ('Retained Earnings',                            800.0),
                ('Total EQUITY',                                 250.0),

                ('LIABILITIES + EQUITY',                          50.0),
            ],
        )

        unfolded_lines = self.report._get_unfolded_lines(lines, line_id)
        self.assertLinesValues(
            unfolded_lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Bank and Cash Accounts',                     -3300.0),
                ('code102 account102',                         -2000.0),
                ('code2 account2',                             -1300.0),
                ('Total Bank and Cash Accounts',               -3300.0),
            ],
        )

    def test_financial_report_comparison(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))
        options['unfolded_lines'] = [line_id]

        lines = self.report._get_lines(options)

        self.assertGrowthComparisonValues(
            lines,
            [
                ('ASSETS',                                      '-80.0%',       'number color-red'),
                ('Current Assets',                              '27.7%',        'number color-red'),
                ('Bank and Cash Accounts',                      '10.0%',        'number color-red'),
                ('code102 account102',                          '0.0%',         'number'),
                ('code2 account2',                              '30.0%',        'number color-red'),
                ('Total Bank and Cash Accounts',                '10.0%',        'number color-red'),
                ('Receivables',                                 '4.4%',         'number color-green'),
                ('Current Assets',                              'n/a',          'number'),
                ('Prepayments',                                 '44.0%',        'number color-red'),
                ('Total Current Assets',                        '27.7%',        'number color-red'),
                ('Plus Fixed Assets',                           '',             ''),
                ('Plus Non-current Assets',                     '20.0%',        'number color-green'),
                ('Total ASSETS',                                '-80.0%',       'number color-red'),

                ('LIABILITIES',                                 'n/a',          'number'),
                ('Current Liabilities',                         'n/a',          'number'),
                ('Current Liabilities',                         '',             ''),
                ('Payables',                                    'n/a',          'number'),
                ('Total Current Liabilities',                   'n/a',          'number'),
                ('Plus Non-current Liabilities',                '',             ''),
                ('Total LIABILITIES',                           'n/a',          'number'),

                ('EQUITY',                                      '0.0%',         'number'),
                ('Unallocated Earnings',                        '-320.0%',      'number color-red'),
                ('Current Year Unallocated Earnings',           '-420.0%',      'number color-red'),
                ('Current Year Earnings',                       '-100.0%',      'number color-red'),
                ('Current Year Allocated Earnings',             'n/a',          'number'),
                ('Total Current Year Unallocated Earnings',     '-420.0%',      'number color-red'),
                ('Previous Years Unallocated Earnings',         'n/a',          'number'),
                ('Total Unallocated Earnings',                  '-320.0%',      'number color-red'),
                ('Retained Earnings',                           'n/a',          'number'),
                ('Total EQUITY',                                '0.0%',         'number'),


                ('LIABILITIES + EQUITY',                        '-80.0%',       'number color-green'),
            ]
        )

    def test_financial_report_horizontal_group(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_receivable0')
        self.report.horizontal_group_ids |= self.horizontal_group

        options = self._generate_options(
            self.report,
            fields.Date.from_string('2019-01-01'),
            fields.Date.from_string('2019-12-31'),
            default_options={
                'unfolded_lines': [line_id],
                'selected_horizontal_group_id': self.horizontal_group.id,
            }
        )
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))

        lines = self.report._get_lines(options)
        self.assertHeadersValues(
            options['column_headers'],
            [
                ['As of 12/31/2019', 'As of 12/31/2018'],
                ['partner_a', 'partner_b'],
                ['code0 account0', 'code1 account1'],
            ]
        )
        self.assertLinesValues(
            lines,
            [   0,                                          1,                   2,                  3,                  4,                  5,                  6,                  7,                  8],
            [
                ('ASSETS',                                  1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),
                ('Current Assets',                          1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),
                ('Bank and Cash Accounts',                  '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Receivables',                             1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),
                ('code0 account0',                          1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),
                ('Total Receivables',                       1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),
                ('Current Assets',                          '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Prepayments',                             '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Total Current Assets',                    1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),
                ('Plus Fixed Assets',                       '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Plus Non-current Assets',                 '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Total ASSETS',                            1300.0,              '',                 25.0,               '',                 1250.0,             '',                 '',                 ''),

                ('LIABILITIES',                             '',                  '',                 '',                -200.0,              '',                 '',                 '',                 ''),
                ('Current Liabilities',                     '',                  '',                 '',                -200.0,              '',                 '',                 '',                 ''),
                ('Current Liabilities',                     '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Payables',                                '',                  '',                 '',                -200.0,              '',                 '',                 '',                 ''),
                ('Total Current Liabilities',               '',                  '',                 '',                -200.0,              '',                 '',                 '',                 ''),
                ('Plus Non-current Liabilities',            '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Total LIABILITIES',                       '',                  '',                 '',                -200.0,              '',                 '',                 '',                 ''),

                ('EQUITY',                                  '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Unallocated Earnings',                    '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Current Year Unallocated Earnings',       '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Current Year Earnings',                   '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Current Year Allocated Earnings',         '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Total Current Year Unallocated Earnings', '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Previous Years Unallocated Earnings',     '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Total Unallocated Earnings',              '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Retained Earnings',                       '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),
                ('Total EQUITY',                            '',                  '',                 '',                 '',                 '',                 '',                 '',                 ''),

                ('LIABILITIES + EQUITY',                    '',                  '',                 '',                -200.0,              '',                 '',                 '',                 ''),
            ],
        )

    def test_hide_if_zero_with_no_formulas(self):
        """
        Check if a report line stays displayed when hide_if_zero is True and no formulas
        is set on the line but has some child which have balance != 0
        We check also if the line is hidden when all its children have balance == 0
        """
        account1, account2 = self.env['account.account'].create([{
            'name': "test_financial_report_1",
            'code': "42241",
            'account_type': "asset_fixed",
        }, {
            'name': "test_financial_report_2",
            'code': "42242",
            'account_type': "asset_fixed",
        }])

        moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2019-04-01',
                'line_ids': [
                    (0, 0, {'debit': 3.0, 'credit': 0.0, 'account_id': account1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2019-05-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 1.0, 'account_id': account2.id}),
                    (0, 0, {'debit': 1.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2019-04-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': account2.id}),
                    (0, 0, {'debit': 3.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
        ])
        moves.action_post()
        moves.line_ids.flush_recordset()

        report = self.env["account.report"].create({
            'name': "test_financial_report_sum",
            'column_ids': [
                Command.create({
                    'name': "Balance",
                    'expression_label': 'balance',
                    'sequence': 1,
                }),
            ],
            'line_ids': [
                Command.create({
                    'name': "Title",
                    'code': 'TT',
                    'hide_if_zero': True,
                    'sequence': 0,
                    'children_ids': [
                        Command.create({
                            'name': "report_line_1",
                            'code': 'TEST_L1',
                            'sequence': 1,
                            'expression_ids': [
                                Command.create({
                                    'label': 'balance',
                                    'engine': 'domain',
                                    'formula': f"[('account_id', '=', {account1.id})]",
                                    'subformula': 'sum',
                                    'date_scope': 'normal',
                                }),
                            ],
                        }),
                        Command.create({
                            'name': "report_line_2",
                            'code': 'TEST_L2',
                            'sequence': 2,
                            'expression_ids': [
                                Command.create({
                                    'label': 'balance',
                                    'engine': 'domain',
                                    'formula': f"[('account_id', '=', {account2.id})]",
                                    'subformula': 'sum',
                                    'date_scope': 'normal',
                                }),
                            ],
                        }),
                    ]
                }),
            ],
        })

        # TODO without this, the create() puts newIds in the sublines, and flushing doesn't help. Seems to be an ORM bug.
        self.env.invalidate_all()

        options = self._generate_options(report, fields.Date.from_string('2019-05-01'), fields.Date.from_string('2019-05-01'))
        options = self._update_comparison_filter(options, report, 'previous_period', 2)

        self.assertLinesValues(
            report._get_lines(options),
            [   0,                                   1,       2,       3],
            [
                ("Title",                           '',      '',      ''),
                ("report_line_1",                  3.0,     3.0,      ''),
                ("report_line_2",                 -4.0,    -3.0,      ''),
            ]
        )

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-05-01',
            'line_ids': [
                (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': account1.id}),
                (0, 0, {'debit': 4.0, 'credit': 0.0, 'account_id': account2.id}),
                (0, 0, {'debit': 0.0, 'credit': 1.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        move.action_post()
        move.line_ids.flush_recordset()

        # With the comparison still on, the lines shouldn't be hidden
        self.assertLinesValues(
            report._get_lines(options),
            [   0,                                   1,       2,       3],
            [
                ("Title",                           '',      '',      ''),
                ("report_line_1",                   '',     3.0,      ''),
                ("report_line_2",                   '',    -3.0,      ''),
            ]
        )

        # Removing the comparison should hide the lines, as they will be 0 in every considered period (the current one)
        options = self._update_comparison_filter(options, report, 'previous_period', 0)
        self.assertLinesValues(report._get_lines(options), [0, 1, 2, 3], [])
