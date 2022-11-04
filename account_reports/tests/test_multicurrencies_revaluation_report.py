# -*- coding: utf-8 -*-
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMultiCurrenciesRevaluationReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_2 = cls.setup_multi_currency_data({
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=10.0, rate2017=20.0)

        cls.receivable_account_1 = cls.company_data['default_account_receivable']
        cls.receivable_account_2 = cls.copy_account(cls.company_data['default_account_receivable'])

        cls.receivable_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({
                    'name': 'receivable_line_1',
                    'debit': 800.0,
                    'credit': 0.0,
                    'currency_id': cls.currency_data['currency'].id,
                    'amount_currency': 2000.0,
                    'account_id': cls.receivable_account_1.id,
                }),
                Command.create({
                    'name': 'receivable_line_2',
                    'debit': 200.0,
                    'credit': 0.0,
                    'currency_id': cls.currency_data['currency'].id,
                    'amount_currency': 500.0,
                    'account_id': cls.receivable_account_2.id,
                }),
                Command.create({
                    'name': 'revenue_line',
                    'debit': 0.0,
                    'credit': 1000.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                }),
            ],
        })
        cls.receivable_move.action_post()
        cls.report = cls.env.ref('account_reports.multicurrency_revaluation_report')

    def test_same_currency(self):
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({
                    'name': 'receivable_line',
                    'debit': 0.0,
                    'credit': 400.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1300.0,
                    'account_id': self.receivable_account_1.id,
                }),
                Command.create({
                    'name': 'bank_line',
                    'debit': 400.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        payment_move.action_post()
        (payment_move + self.receivable_move).line_ids\
            .filtered(lambda line: line.account_id == self.receivable_account_1)\
            .reconcile()

        self.env.invalidate_all()

        # Test the report in 2016.
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'))
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            [   0,                                           1,             2,              3,               4],
            [
                ('Accounts To Adjust',                      '',             '',             '',              ''),
                ('Gol (1 USD = 3.0 Gol)',               1200.0,          480.0,          400.0,          -80.00),
                ('121000 Account Receivable',            700.0,          280.0,         233.33,          -46.67),
                ('INV/2016/00001 receivable_line_1',     700.0,          280.0,         233.33,          -46.67),
                ('Total 121000 Account Receivable',      700.0,          280.0,         233.33,          -46.67),
                ('121000.1 Account Receivable',        500.0,          200.0,         166.67,          -33.33),
                ('INV/2016/00001 receivable_line_2',     500.0,          200.0,         166.67,          -33.33),
                ('Total 121000.1 Account Receivable',  500.0,          200.0,         166.67,          -33.33),
                ('Total Gol',                           1200.0,          480.0,          400.0,           -80.0),
            ],
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        # I don't understand why this is necessary
        self.env.invalidate_all()

        # Test the report in 2017.
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfold_all'] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            [   0,                                                   1,              2,              3,              4],
            [
                ('Accounts To Adjust',                              '',             '',             '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                       1200.0,          480.0,          600.0,          120.0),
                ('121000 Account Receivable',                    700.0,          280.0,          350.0,           70.0),
                ('INV/2016/00001 receivable_line_1',             700.0,          280.0,          350.0,           70.0),
                ('Total 121000 Account Receivable',              700.0,          280.0,          350.0,           70.0),
                ('121000.1 Account Receivable',                500.0,          200.0,          250.0,           50.0),
                ('INV/2016/00001 receivable_line_2',             500.0,          200.0,          250.0,           50.0),
                ('Total 121000.1 Account Receivable',          500.0,          200.0,          250.0,           50.0),
                ('Total Gol',                                   1200.0,          480.0,          600.0,          120.0),
            ],
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        self.env.context = {**self.env.context, **options}
        wizard = self.env['account.multicurrency.revaluation.wizard'].create({
            'journal_id': self.company_data['default_journal_misc'].id,
            'expense_provision_account_id': self.company_data['default_account_expense'].id,
            'income_provision_account_id': self.company_data['default_account_revenue'].id,
        })
        provision_move_id = wizard.create_entries()['res_id']
        self.assertRecordValues(
            self.env['account.move'].browse(provision_move_id).line_ids,
            [
                {'account_id': self.receivable_account_1.id, 'debit': 70, 'credit': 0},
                {'account_id': wizard.income_provision_account_id.id, 'debit': 0, 'credit': 70},
                {'account_id': self.receivable_account_2.id, 'debit': 50, 'credit': 0},
                {'account_id': wizard.income_provision_account_id.id, 'debit': 0, 'credit': 50},
            ]
        )

    def test_multi_currencies(self):
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({
                    'name': 'receivable_line',
                    'debit': 0.0,
                    'credit': 100.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1300.0,
                    'account_id': self.receivable_account_1.id,
                }),
                Command.create({
                    'name': 'receivable_line',
                    'debit': 0.0,
                    'credit': 250.0,
                    'currency_id': self.currency_data_2['currency'].id,
                    'amount_currency': -5250.0,
                    'account_id': self.receivable_account_1.id,
                }),
                Command.create({
                    'name': 'receivable_line',
                    'debit': 0.0,
                    'credit': 50.0,
                    'account_id': self.receivable_account_1.id,
                }),
                Command.create({
                    'name': 'bank_line',
                    'debit': 400.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        payment_move.action_post()
        (payment_move + self.receivable_move).line_ids\
            .filtered(lambda line: line.account_id == self.receivable_account_1)\
            .reconcile()

        # Test the report in 2017.
        options = self._generate_options(self.report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2017-01-01'))
        options['unfold_all'] = True

        # Check the gold currency.
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            [   0,                                                 1,          2,          3,          4],
            [
                ('Accounts To Adjust',                            '',         '',         '',         ''),
                ('Gol (1 USD = 2.0 Gol)',                      500.0,      200.0,      250.0,       50.0),
                ('121000.1 Account Receivable',              500.0,      200.0,      250.0,       50.0),
                ('INV/2016/00001 receivable_line_2',           500.0,      200.0,      250.0,       50.0),
                ('Total 121000.1 Account Receivable',        500.0,      200.0,      250.0,       50.0),
                ('Total Gol',                                  500.0,      200.0,      250.0,       50.0),
            ],
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

    def test_exclude_account_for_adjustment_entry(self):
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2017-01-01',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                Command.create({
                    'name': 'receivable_line',
                    'debit': 0.0,
                    'credit': 400.0,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1300.0,
                    'account_id': self.receivable_account_1.id,
                }),
                Command.create({
                    'name': 'bank_line',
                    'debit': 400.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })
        payment_move.action_post()
        (payment_move + self.receivable_move).line_ids\
            .filtered(lambda line: line.account_id == self.receivable_account_1)\
            .reconcile()

        # Test the report in 2017.
        options = self._generate_options(self.report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))
        options['unfold_all'] = True
        self.env['account.multicurrency.revaluation.report.handler'].action_multi_currency_revaluation_toggle_provision(
            options,
            {
                'account_id': self.receivable_account_1.id,
                'currency_id': self.currency_data['currency'].id
            }
        )

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            [   0,                                                   1,              2,              3,              4],
            [
                ('Accounts To Adjust',                              '',             '',             '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                        500.0,          200.0,          250.0,           50.0),
                ('121000.1 Account Receivable',                500.0,          200.0,          250.0,           50.0),
                ('INV/2016/00001 receivable_line_2',             500.0,          200.0,          250.0,           50.0),
                ('Total 121000.1 Account Receivable',          500.0,          200.0,          250.0,           50.0),
                ('Total Gol',                                    500.0,          200.0,          250.0,           50.0),

                ('Excluded Accounts',                               '',             '',             '',             ''),
                ('Gol (1 USD = 2.0 Gol)',                        700.0,          280.0,          350.0,           70.0),
                ('121000 Account Receivable',                    700.0,          280.0,          350.0,           70.0),
                ('INV/2016/00001 receivable_line_1',             700.0,          280.0,          350.0,           70.0),
                ('Total 121000 Account Receivable',              700.0,          280.0,          350.0,           70.0),
                ('Total Gol',                                    700.0,          280.0,          350.0,           70.0),
            ],
            currency_map={
                1: {'currency': self.currency_data['currency']},
            },
        )

        self.env.context = {**self.env.context, **options}
        wizard = self.env['account.multicurrency.revaluation.wizard'].create({
            'journal_id': self.company_data['default_journal_misc'].id,
            'expense_provision_account_id': self.company_data['default_account_expense'].id,
            'income_provision_account_id': self.company_data['default_account_revenue'].id,
        })
        provision_move_id = wizard.create_entries()['res_id']
        self.assertRecordValues(
            self.env['account.move'].browse(provision_move_id).line_ids,
            [
                {'account_id': self.receivable_account_2.id, 'debit': 50, 'credit': 0},
                {'account_id': wizard.income_provision_account_id.id, 'debit': 0, 'credit': 50},
            ]
        )
