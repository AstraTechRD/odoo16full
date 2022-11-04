# -*- coding: utf-8 -*-
# pylint: disable=C0326
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAgedPayableReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_category_b = cls.env['res.partner.category'].create({'name': 'partner_categ_b'})

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False, 'category_id': [Command.set([cls.partner_category_a.id, cls.partner_category_b.id])]})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False, 'category_id': [Command.set([cls.partner_category_a.id])]})

        payable_1 = cls.company_data['default_account_payable']
        payable_2 = cls.company_data['default_account_payable'].copy()
        payable_3 = cls.company_data['default_account_payable'].copy()
        payable_4 = cls.company_data_2['default_account_payable']
        payable_5 = cls.company_data_2['default_account_payable'].copy()
        payable_6 = cls.company_data_2['default_account_payable'].copy()
        misc_1 = cls.company_data['default_account_expense']
        misc_2 = cls.company_data_2['default_account_expense']

        # Test will use the following dates:
        # As of                  2017-02-01
        # 1 - 30:   2017-01-31 - 2017-01-02
        # 31 - 60:  2017-01-01 - 2016-12-03
        # 61 - 90:  2016-12-02 - 2016-11-03
        # 91 - 120: 2016-11-02 - 2016-10-04
        # Older:    2016-10-03

        # ==== Journal entries in company_1 for partner_a ====

        move_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-11-03'),
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'line_ids': [
                # 1000.0 in 61 - 90.
                Command.create({'debit': 0.0,       'credit': 1000.0,   'date_maturity': False,         'account_id': payable_1.id,      'partner_id': cls.partner_a.id}),
                # -800.0 in 31 - 60
                Command.create({'debit': 800.0,     'credit': 0.0,      'date_maturity': '2017-01-01',  'account_id': payable_2.id,      'partner_id': cls.partner_a.id}),
                # Ignored line.
                Command.create({'debit': 200.0,     'credit': 0.0,      'date_maturity': False,         'account_id': misc_1.id,         'partner_id': cls.partner_a.id}),
            ],
        })

        move_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-10-05'),
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'line_ids': [
                # -200.0 in 61 - 90
                Command.create({'debit': 200.0,    'credit': 0.0,        'date_maturity': '2016-12-02',  'account_id': payable_1.id,      'partner_id': cls.partner_a.id}),
                # -300.0 in 31 - 60
                Command.create({'debit': 300.0,    'credit': 0.0,        'date_maturity': '2016-12-03',  'account_id': payable_1.id,      'partner_id': cls.partner_a.id}),
                # 1000.0 in 91 - 120
                Command.create({'debit': 0.0,      'credit': 1000.0,     'date_maturity': False,         'account_id': payable_2.id,      'partner_id': cls.partner_a.id}),
                # 100.0 in all dates
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2017-02-01',  'account_id': payable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2017-01-02',  'account_id': payable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-12-03',  'account_id': payable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-11-03',  'account_id': payable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-10-04',  'account_id': payable_3.id,      'partner_id': cls.partner_a.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-01-01',  'account_id': payable_3.id,      'partner_id': cls.partner_a.id}),
                # Ignored line.
                Command.create({'debit': 1100.0,   'credit': 0.0,        'date_maturity': '2016-10-05',  'account_id': misc_1.id,         'partner_id': cls.partner_a.id}),
            ],
        })
        (move_1 + move_2).action_post()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == payable_1).reconcile()
        (move_1 + move_2).line_ids.filtered(lambda line: line.account_id == payable_2).reconcile()

        # ==== Journal entries in company_2 for partner_b ====

        move_3 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-11-03'),
            'journal_id': cls.company_data_2['default_journal_purchase'].id,
            'line_ids': [
                # 1000.0 in 61 - 90.
                Command.create({'debit': 0.0,       'credit': 1000.0,   'date_maturity': False,         'account_id': payable_4.id,      'partner_id': cls.partner_b.id}),
                # -800.0 in 31 - 60
                Command.create({'debit': 800.0,     'credit': 0.0,      'date_maturity': '2017-01-01',  'account_id': payable_5.id,      'partner_id': cls.partner_b.id}),
                # Ignored line.
                Command.create({'debit': 200.0,     'credit': 0.0,      'date_maturity': False,         'account_id': misc_2.id,         'partner_id': cls.partner_b.id}),
            ],
        })

        move_4 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-10-05'),
            'journal_id': cls.company_data_2['default_journal_purchase'].id,
            'line_ids': [
                # -200.0 in 61 - 90
                Command.create({'debit': 200.0,    'credit': 0.0,        'date_maturity': '2016-12-02',  'account_id': payable_4.id,      'partner_id': cls.partner_b.id}),
                # -300.0 in 31 - 60
                Command.create({'debit': 300.0,    'credit': 0.0,        'date_maturity': '2016-12-03',  'account_id': payable_4.id,      'partner_id': cls.partner_b.id}),
                # 1000.0 in 91 - 120
                Command.create({'debit': 0.0,      'credit': 1000.0,     'date_maturity': False,         'account_id': payable_5.id,      'partner_id': cls.partner_b.id}),
                # 100.0 in all dates
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2017-02-01',  'account_id': payable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2017-01-02',  'account_id': payable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-12-03',  'account_id': payable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-11-03',  'account_id': payable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-10-04',  'account_id': payable_6.id,      'partner_id': cls.partner_b.id}),
                Command.create({'debit': 0.0,      'credit': 100.0,      'date_maturity': '2016-01-01',  'account_id': payable_6.id,      'partner_id': cls.partner_b.id}),
                # Ignored line.
                Command.create({'debit': 1100.0,   'credit': 0.0,        'date_maturity': '2016-10-05',  'account_id': misc_2.id,         'partner_id': cls.partner_b.id}),
            ],
        })
        (move_3 + move_4).action_post()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == payable_4).reconcile()
        (move_3 + move_4).line_ids.filtered(lambda line: line.account_id == payable_5).reconcile()
        cls.env['res.currency'].search([('name', '!=', 'USD')]).active = False
        cls.env.companies = cls.company_data['company'] + cls.company_data_2['company']
        cls.report = cls.env.ref('account_reports.aged_payable_report')
        cls.prefix_line_id = f'{cls._get_basic_line_dict_id_from_report_line_ref("account_reports.aged_payable_line")}|'

    def test_aged_payable_unfold_1_whole_report(self):
        """ Test unfolding a line when rendering the whole report. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        partner_a_line_id = f'{self.prefix_line_id}groupby:partner_id-res.partner-{self.partner_a.id}'
        options['unfolded_lines'] = [partner_a_line_id]

        report_lines = self.report._get_lines(options)
        sorted_report_lines = self.report._sort_lines(report_lines, options)
        self.assertLinesValues(
            # pylint: disable=C0326
            sorted_report_lines,
            #   Name                    Due Date   Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                                 1,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',                  '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',    50.0,      50.0,        50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Payable',            '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

        # Sort 61 - 90 decreasing.
        options['order_column'] = -7
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(sorted_report_lines, options),
            #   Name                    Due Date   Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                                 1,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',                  '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_b',                     '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('Total Aged Payable',            '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

        # Sort 61 - 90 increasing.
        options['order_column'] = 7
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(sorted_report_lines, options),
            #   Name                    Due Date    Not Due On      1 - 30     31 - 60      61 - 90    91 - 120       Older        Total
            [   0,                                 1,        4,          5,          6,           7,          8,          9,          10],
            [
                ('Aged Payable',                  '',    150.0,      150.0,      150.0,       900.0,      450.0,      150.0,      1950.0),
                ('partner_b',                     '',     50.0,       50.0,       50.0,       300.0,      150.0,       50.0,       650.0),
                ('partner_a',                     '',    100.0,      100.0,      100.0,       600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/10/0001',   '01/01/2016',       '',         '',         '',          '',         '',      100.0,          ''),
                ('BILL/2016/10/0001',   '10/04/2016',       '',         '',         '',          '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',       '',         '',         '',          '',      200.0,         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',       '',         '',      100.0,          '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',       '',      100.0,         '',          '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '02/01/2017',    100.0,         '',         '',          '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',       '',         '',         '',       100.0,         '',         '',          ''),
                ('BILL/2016/11/0001',   '11/03/2016',       '',         '',         '',       500.0,         '',         '',          ''),
                ('Total partner_a',               '',    100.0,      100.0,      100.0,       600.0,      300.0,      100.0,      1300.0),
                ('Total Aged Payable',            '',    150.0,      150.0,      150.0,       900.0,      450.0,      150.0,      1950.0),
            ],
        )

    def test_aged_payable_unknown_partner(self):
        """ Test that journal items without a partner in the payable account appear as unknown partner. """

        misc_move = self.env['account.move'].create({
            'date': '2017-03-31',
            'line_ids': [
                Command.create({'debit': 0.0, 'credit': 1000.0, 'account_id': self.company_data['default_account_expense'].id}),
                Command.create({'debit': 1000.0, 'credit': 0.0, 'account_id': self.company_data['default_account_payable'].id}),
            ],
        })
        misc_move.action_post()

        options = self._generate_options(self.report, fields.Date.from_string('2017-03-01'), fields.Date.from_string('2017-04-01'))
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name               Due Date     Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       1,             4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',        '',            '',    -1000.0,      150.0,      150.0,      150.0,     1500.0,       950.0),
                ('partner_a',           '',            '',         '',      100.0,      100.0,      100.0,     1000.0,      1300.0),
                ('partner_b',           '',            '',         '',       50.0,       50.0,       50.0,      500.0,       650.0),
                ('Unknown',             '',            '',    -1000.0,         '',         '',         '',         '',     -1000.0),
            ],
        )

    def test_aged_payable_filter_partners(self):
        """ Test the filter on top allowing to filter on res.partner. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['partner_ids'] = self.partner_a.ids
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name              Due Date      Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       1,             4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',        '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_a',           '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
            ],
        )

    def test_aged_payable_filter_partner_categories(self):
        """ Test the filter on top allowing to filter on res.partner.category. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        options['partner_categories'] = self.partner_category_a.ids
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name               Due Date     Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older        Total
            [   0,                       1,             4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',        '',         150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',           '',         100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('partner_b',           '',          50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
            ],
        )

    def test_aged_payable_reconciliation_date(self):
        """ Check the values at a date before some reconciliations are done. """
        options = self._generate_options(self.report, fields.Date.from_string('2016-10-31'), fields.Date.from_string('2016-10-31'))
        self.env.company.totals_below_sections = False

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name               Due Date  Not Due On      1 - 30     31 - 60     61 - 90    91 - 120       Older       Total
            [   0,                       1,         4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',        '',   -133.35,    1466.66,         '',         '',         '',     133.33,    1466.64),
                ('partner_a',           '',   -100.00,    1100.00,         '',         '',         '',     100.00,    1100.00),
                ('partner_b',           '',    -33.35,     366.66,         '',         '',         '',      33.33,     366.64),
            ],
        )

    def test_aged_payable_sort_lines_by_date(self):
        """ Test the sort_lines function using date as sort key. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        partner_a_line_id = f'{self.prefix_line_id}groupby:partner_id-res.partner-{self.partner_a.id}'
        partner_b_line_id = f'{self.prefix_line_id}groupby:partner_id-res.partner-{self.partner_b.id}'
        options['unfolded_lines'] = [partner_a_line_id, partner_b_line_id]

        report_lines = self.report._get_lines(options)
        options['order_column'] = 1 # Sort by Due Date increasing
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(report_lines, options),
            #   Name                        Due Date   Not Due On   1 - 30     31 - 60     61 - 90    91 - 120        Older        Total
            [   0,                                 1,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',                  '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',          '',        '',       50.0,          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',          '',      50.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',          '',     100.0,         '',          ''),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',       250.0,        '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',        50.0,        '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',       50.0,          '',        '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',       50.0,         '',          '',        '',         '',          ''),
                ('BILL/2016/10/0001',   '02/01/2017',    50.0,         '',         '',          '',        '',         '',          ''),
                ('Total partner_b',               '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Payable',            '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

        options['order_column'] = -1 # Sort by Due Date decreasing
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(report_lines, options),
            #   Name                    Due Date     Not Due On     1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                 1,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',                  '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/10/0001',   '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                     '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('BILL/2016/10/0001',   '02/01/2017',    50.0,         '',         '',          '',        '',         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',       50.0,         '',          '',        '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',       50.0,          '',        '',         '',          ''),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',       250.0,        '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',        50.0,        '',         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',          '',     100.0,         '',          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',          '',      50.0,         '',          ''),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',          '',        '',       50.0,          ''),
                ('Total partner_b',               '',    50.0,       50.0,       50.0,       300.0,     150.0,       50.0,       650.0),
                ('Total Aged Payable',            '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

    def test_aged_payable_sort_lines_by_numeric_value(self):
        """ Test the sort_lines function using float as sort key. """
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))
        partner_a_line_id = f'{self.prefix_line_id}groupby:partner_id-res.partner-{self.partner_a.id}'
        partner_b_line_id = f'{self.prefix_line_id}groupby:partner_id-res.partner-{self.partner_b.id}'
        options['unfolded_lines'] = [partner_a_line_id, partner_b_line_id]

        report_lines = self.report._get_lines(options)
        options['order_column'] = 4 # Sort by Not Due On increasing
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(report_lines, options),
            #   Name                    Due Date     Not Due On     1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                 1,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',                  '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_b',                     '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',      250.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',       50.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',       50.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',       50.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',         '',       50.0,         '',          ''),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',         '',         '',       50.0,          ''),
                ('BILL/2016/10/0001',   '02/01/2017',    50.0,         '',         '',         '',         '',         '',          ''),
                ('Total partner_b',               '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('partner_a',                     '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/11/0001',   '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('BILL/2016/10/0001',   '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',   '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('BILL/2016/10/0001',   '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',   '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('BILL/2016/10/0001',   '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('Total partner_a',               '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('Total Aged Payable',            '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )

        options['order_column'] = -4 # Sort by Not Due On decreasing
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._sort_lines(report_lines, options),
            #   Name                    Due Date     Not Due On     1 - 30     31 - 60     61 - 90    91 - 120       Older         Total
            [   0,                                 1,       4,          5,          6,          7,          8,          9,          10],
            [
                ('Aged Payable',                   '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
                ('partner_a',                      '',   100.0,      100.0,      100.0,      600.0,      300.0,      100.0,      1300.0),
                ('BILL/2016/10/0001',    '02/01/2017',   100.0,         '',         '',         '',         '',         '',          ''),
                ('BILL/2016/11/0001',    '11/03/2016',      '',         '',         '',      500.0,         '',         '',          ''),
                ('BILL/2016/10/0001',    '10/05/2016',      '',         '',         '',         '',      200.0,         '',          ''),
                ('BILL/2016/10/0001',    '01/02/2017',      '',      100.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',    '12/03/2016',      '',         '',      100.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',    '11/03/2016',      '',         '',         '',      100.0,         '',         '',          ''),
                ('BILL/2016/10/0001',    '10/04/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',    '01/01/2016',      '',         '',         '',         '',         '',      100.0,          ''),
                ('Total partner_a',                '',   100.0,      100.0,      100.0,       600.0,     300.0,      100.0,      1300.0),
                ('partner_b',                      '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('BILL/2016/10/0001',    '02/01/2017',    50.0,         '',         '',         '',         '',         '',          ''),
                ('BILL/2016/11/0001',    '11/03/2016',      '',         '',         '',      250.0,         '',         '',          ''),
                ('BILL/2016/10/0001',    '10/05/2016',      '',         '',         '',         '',      100.0,         '',          ''),
                ('BILL/2016/10/0001',    '01/02/2017',      '',       50.0,         '',         '',         '',         '',          ''),
                ('BILL/2016/10/0001',    '12/03/2016',      '',         '',       50.0,         '',         '',         '',          ''),
                ('BILL/2016/10/0001',    '11/03/2016',      '',         '',         '',       50.0,         '',         '',          ''),
                ('BILL/2016/10/0001',    '10/04/2016',      '',         '',         '',         '',       50.0,         '',          ''),
                ('BILL/2016/10/0001',    '01/01/2016',      '',         '',         '',         '',         '',       50.0,          ''),
                ('Total partner_b',                '',    50.0,       50.0,       50.0,      300.0,      150.0,       50.0,       650.0),
                ('Total Aged Payable',             '',   150.0,      150.0,      150.0,      900.0,      450.0,      150.0,      1950.0),
            ],
        )
