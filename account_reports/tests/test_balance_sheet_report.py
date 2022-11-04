# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=bad-whitespace
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBalanceSheetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.report = cls.env.ref('account_reports.balance_sheet')

    def test_report_lines_ordering(self):
        """ Check that the report lines are correctly ordered with nested account groups """
        self.env['account.group'].create([{
            'name': 'A',
            'code_prefix_start': '101402',
            'code_prefix_end': '101601',
        }, {
            'name': 'A1',
            'code_prefix_start': '1014040',
            'code_prefix_end': '1015010',
        }])

        def find_account(code):
            return self.env['account.account'].search([('code', '=', code), ('company_id', '=', self.env.company.id)])

        account_bank = find_account('101404')
        account_cash = find_account('101501')
        account_a = self.env['account.account'].create([{'code': '1014040', 'name': 'A', 'account_type': 'asset_cash'}])
        account_c = self.env['account.account'].create([{'code': '101600', 'name': 'C', 'account_type': 'asset_cash'}])

        # Create a journal lines for each account
        move = self.env['account.move'].create({
            'date': '2020-02-02',
            'line_ids': [
                Command.create({
                    'account_id': account.id,
                    'name': 'name',
                })
                for account in [account_a, account_c, account_bank, account_cash]
            ],
        })
        move.action_post()
        move.line_ids.flush_recordset()

        # Create the report hierarchy with the Bank and Cash Accounts lines unfolded
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(
            self.report,
            fields.Date.from_string('2020-02-01'),
            fields.Date.from_string('2020-02-28')
        )
        options['unfolded_lines'] = [line_id]
        lines = self.report._get_lines(options)
        lines = self.report._create_hierarchy(lines, options)

        # The Bank and Cash Accounts section start at index 2
        # Since we created 4 lines + 2 groups, we keep the 6 following lines
        unfolded_lines = self.report._get_unfolded_lines(lines, line_id)
        unfolded_lines = [{'name': line['name'], 'level': line['level']} for line in unfolded_lines]

        self.assertEqual(
            unfolded_lines,
            [
                {'level': 5, 'name': 'Bank and Cash Accounts'},
                {'level': 6, 'name': '101402-101601 A'},
                {'level': 7, 'name': '101404 Bank'},
                {'level': 7, 'name': '1014040-1015010 A1'},
                {'level': 8, 'name': '1014040 A'},
                {'level': 8, 'name': '101501 Cash'},
                {'level': 7, 'name': '101600 C'},
                {'level': 6, 'name': 'Total Bank and Cash Accounts'},
            ]
        )

    def test_balance_sheet_custom_date(self):
        line_id = self.env.ref('account_reports.account_financial_report_bank_view0').id
        options = self._generate_options(self.report, fields.Date.from_string('2020-02-01'), fields.Date.from_string('2020-02-28'))
        options['date']['filter'] = 'custom'
        options['unfolded_lines'] = [line_id]
        options.pop('multi_company', None)

        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2020-0%s-15' % i,
            'invoice_date': '2020-0%s-15' % i,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        } for i in range(1, 4)])
        invoices.action_post()

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      2300.00),
                ('Current Assets',                              2300.00),
                ('Bank and Cash Accounts',                      ''),
                ('Receivables',                                 2300.00),
                ('Current Assets',                              ''),
                ('Prepayments',                                 ''),
                ('Total Current Assets',                        2300.00),
                ('Plus Fixed Assets',                           ''),
                ('Plus Non-current Assets',                     ''),
                ('Total ASSETS',                                2300.00),

                ('LIABILITIES',                                 300.00),
                ('Current Liabilities',                         300.00),
                ('Current Liabilities',                         300.00),
                ('Payables',                                    ''),
                ('Total Current Liabilities',                   300.00),
                ('Plus Non-current Liabilities',                ''),
                ('Total LIABILITIES',                           300.00),

                ('EQUITY',                                      2000.00),
                ('Unallocated Earnings',                        2000.00),
                ('Current Year Unallocated Earnings',           2000.00),
                ('Current Year Earnings',                       2000.00),
                ('Current Year Allocated Earnings',             ''),
                ('Total Current Year Unallocated Earnings',     2000.00),
                ('Previous Years Unallocated Earnings',         ''),
                ('Total Unallocated Earnings',                  2000.00),
                ('Retained Earnings',                           ''),
                ('Total EQUITY',                                2000.00),
                ('LIABILITIES + EQUITY',                        2300.00),
            ],
        )
