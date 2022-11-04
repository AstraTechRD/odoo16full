from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged
from odoo.tools import frozendict

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestReportEngines(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].totals_below_sections = False

        cls.garbage_account = cls.env['account.account'].create({
            'code': "turlututu",
            'name': "turlututu",
            'account_type': "asset_current",
        })

        cls.fake_country = cls.env['res.country'].create({
            'name': "L'Île de la Mouche",
            'code': 'YY',
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _prepare_test_account_move_line(self, balance, account_code=None, tax_tags=None, date='2020-01-01', **kwargs):
        if tax_tags:
            tags = self.env['account.account.tag'].search([
                ('applicability', '=', 'taxes'),
                ('country_id', '=', self.fake_country.id),
                ('name', 'in', tax_tags),
            ])
        else:
            tags = self.env['account.account.tag']

        return {
            'account_move_line_values': {
                'name': "turlututu",
                'account_id': self.garbage_account.id,
                **kwargs,
                'debit': balance if balance > 0.0 else 0.0,
                'credit': -balance if balance < 0.0 else 0.0,
                'tax_tag_ids': [Command.set(tags.ids)],
            },
            'account_move_values': {'date': date},
            'account_code': account_code,
        }

    def _create_test_account_moves(self, test_account_move_line_values_list):
        # Create the missing account on-the-fly.
        accounts_to_create_by_code = set()
        for test_account_move_line_values in test_account_move_line_values_list:
            if test_account_move_line_values.get('account_code'):
                accounts_to_create_by_code.add(test_account_move_line_values['account_code'])

        if accounts_to_create_by_code:
            accounts = self.env['account.account'].create([
                {
                    'code': account_code,
                    'name': account_code,
                    'account_type': "asset_current",
                }
                for account_code in accounts_to_create_by_code
            ])
            account_by_code = {x.code: x for x in accounts}

            for test_account_move_line_values in test_account_move_line_values_list:
                account = account_by_code.get(test_account_move_line_values.get('account_code'))
                if account:
                    test_account_move_line_values['account_move_line_values']['account_id'] = account.id

        # Create the journal entries.
        to_create = {}
        for test_account_move_line_values in test_account_move_line_values_list:
            account_move_key = frozendict(test_account_move_line_values['account_move_values'])
            account_move_line_values = test_account_move_line_values['account_move_line_values']
            account_move_to_create = to_create.setdefault(account_move_key, {
                'account_move_values': {'line_ids': []},
                'balance': 0.0,
            })
            account_move_to_create['account_move_values']['line_ids'].append(Command.create(account_move_line_values))
            account_move_to_create['balance'] += account_move_line_values['debit'] - account_move_line_values['credit']

        account_move_create_list = []
        for account_move_dict, account_move_to_create in to_create.items():
            open_balance = account_move_to_create['balance']
            account_move_values = account_move_to_create['account_move_values']
            if not self.env.company.currency_id.is_zero(open_balance):
                account_move_values['line_ids'].append(Command.create({
                    'name': 'open balance',
                    'account_id': self.garbage_account.id,
                    'debit': -open_balance if open_balance < 0.0 else 0.0,
                    'credit': open_balance if open_balance > 0.0 else 0.0,
                }))
            account_move_create_list.append({
                **account_move_dict,
                **account_move_values,
            })

        moves = self.env['account.move'].create(account_move_create_list)
        moves.action_post()
        return moves

    def _prepare_test_external_values(self, value, date):
        return {
            'name': date,
            'value': value,
            'date': date,
        }

    def _prepare_test_expression(self, formula, **kwargs):
        return {
            'expression_values': {
                'label': 'balance',
                'formula': formula,
                **kwargs,
            },
        }

    def _prepare_test_expression_tax_tags(self, formula, **kwargs):
        return self._prepare_test_expression(engine='tax_tags', formula=formula, **kwargs)

    def _prepare_test_expression_domain(self, formula, subformula, **kwargs):
        return self._prepare_test_expression(engine='domain', formula=formula, subformula=subformula, **kwargs)

    def _prepare_test_expression_account_codes(self, formula, **kwargs):
        return self._prepare_test_expression(engine='account_codes', formula=formula, **kwargs)

    def _prepare_test_expression_external(self, formula, external_value_generators, **kwargs):
        return {
            **self._prepare_test_expression(engine='external', formula=formula, **kwargs),
            'external_value_generators': external_value_generators,
        }

    def _prepare_test_expression_custom(self, formula, **kwargs):
        return self._prepare_test_expression(engine='custom', formula=formula, **kwargs)

    def _prepare_test_expression_aggregation(self, formula, subformula=None, column='balance'):
        return {
            'expression_values': {
                'label': column,
                'engine': 'aggregation',
                'formula': formula,
                'subformula': subformula,
            },
        }

    def _prepare_test_report_line(self, *expression_generators, **kwargs):
        return {
            'report_line_values': {
                **kwargs,
                'expression_ids': [
                    Command.create({
                        'date_scope': 'strict_range',
                        **expression_values['expression_values'],
                    })
                    for expression_values in expression_generators
                ],
            },
            'expression_generators': expression_generators,
        }

    def _create_report(self, test_report_line_values_list, columns=None, **kwargs):
        if not columns:
            columns = ['balance']

        # Create a new report
        report = self.env['account.report'].create({
            'name': "_run_report",
            'filter_date_range': True,
            'filter_unfold_all': True,
            **kwargs,
            'column_ids': [
                Command.create({
                    'name': column,
                    'expression_label': column,
                    'sequence': i,
                })
                for i, column in enumerate(columns)
            ],
            'line_ids': [
                Command.create({
                    'name': f"test_line_{i}",
                    'code': f"test_line_{i}",
                    **test_report_line_values['report_line_values'],
                    'sequence': i,
                })
                for i, test_report_line_values in enumerate(test_report_line_values_list, start=1)
            ],
        })

        # Create the external values
        external_values_create_list = []
        for report_line, test_report_line_values in zip(report.line_ids, test_report_line_values_list):
            for expression, expression_values in zip(report_line.expression_ids, test_report_line_values['expression_generators']):
                for external_values in expression_values.get('external_value_generators', []):
                    external_values_create_list.append({
                        **external_values,
                        'target_report_expression_id': expression.id,
                    })
        self.env['account.report.external.value'].create(external_values_create_list)

        return report

    def _get_audit_params_from_report_line(self, options, report_line, report_line_dict, **kwargs):
        return {
            'report_line_id': report_line.id,
            'calling_line_dict_id': report_line_dict['id'],
            'expression_label': 'balance',
            'column_group_key': next(iter(options['column_groups'])),
            **kwargs,
        }

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    def test_engine_tax_tags(self):
        self.env.company.account_fiscal_country_id = self.fake_country

        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('11'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('222T'),
            groupby='account_id',
        )
        test_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('3333'),
            groupby='account_id',
        )
        report = self._create_report(
            [test_line_1, test_line_2, test_line_3],
            country_id=self.fake_country.id,
        )

        # Create the journal entries.
        move = self._create_test_account_moves([
            self._prepare_test_account_move_line(2000.0, account_code='101001', tax_tags=['+11', '-222T']),
            self._prepare_test_account_move_line(1000.0, account_code='101001', tax_tags=['+11', '-222T']),
            self._prepare_test_account_move_line(3600.0, account_code='101001', tax_tags=['+222T']),
            self._prepare_test_account_move_line(-600.0, account_code='101001', tax_tags=['+222T', '-3333']),
            self._prepare_test_account_move_line(-900.0, account_code='101002', tax_tags=['-11']),
            self._prepare_test_account_move_line(1500.0, account_code='101002', tax_tags=['+11']),
        ])

        options = self._generate_options(report, '2020-01-01', '2020-01-01', default_options={'unfold_all': True})
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',        5400.0),
                ('101001 101001',      3000.0),
                ('101002 101002',      2400.0),
                ('test_line_2',            ''),
                ('101001 101001',          ''),
                ('test_line_3',         600.0),
                ('101001 101001',       600.0),
            ],
        )

        # Check redirection.
        expected_redirection_values_list = [
            move.line_ids[:2] + move.line_ids[4:6],
            move.line_ids[:4],
            move.line_ids[3],
        ]
        for report_line, expected_amls in zip(report.line_ids, expected_redirection_values_list):
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(move.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_domain(self):
        domain = [('account_id.code', '=like', '1%'), ('balance', '<', 0.0)]

        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'sum'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, '-sum'),
            groupby='account_id',
        )
        test_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'sum_if_neg'),
            groupby='account_id',
        )
        test_line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, '-sum_if_neg'),
            groupby='account_id',
        )
        test_line_5 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'sum_if_pos'),
            groupby='account_id',
        )
        test_line_6 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, '-sum_if_pos'),
            groupby='account_id',
        )
        test_line_7 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'count_rows'),
            groupby='account_id',
        )
        report = self._create_report([test_line_1, test_line_2, test_line_3, test_line_4, test_line_5, test_line_6, test_line_7])

        # Create the journal entries.
        move = self._create_test_account_moves([
            self._prepare_test_account_move_line(2000.0, account_code='101001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(-600.0, account_code='101003'),
            self._prepare_test_account_move_line(-900.0, account_code='101004'),
        ])

        # Check the values.
        options = self._generate_options(report, '2020-01-01', '2020-01-01', default_options={'unfold_all': True})
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',       -1800.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('101004 101004',      -900.0),
                ('test_line_2',        1800.0),
                ('101002 101002',       300.0),
                ('101003 101003',       600.0),
                ('101004 101004',       900.0),
                ('test_line_3',       -1800.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('101004 101004',      -900.0),
                ('test_line_4',        1800.0),
                ('101002 101002',       300.0),
                ('101003 101003',       600.0),
                ('101004 101004',       900.0),
                ('test_line_5',            ''),
                ('test_line_6',            ''),
                ('test_line_7',             3),
                ('101002 101002',           1),
                ('101003 101003',           1),
                ('101004 101004',           1),
            ],
        )

        # Check redirection.
        expected_amls = move.line_ids.search(domain)
        for report_line in report.line_ids:
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(move.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_account_codes(self):
        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1C'),
            groupby='account_id',
        )
        test_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1D'),
            groupby='account_id',
        )
        test_line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'-101\(101003)'),
            groupby='account_id',
        )
        test_line_5 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'-101\(101003)C'),
            groupby='account_id',
        )
        test_line_6 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'-101\(101002,101003)'),
            groupby='account_id',
        )
        test_line_7 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10.'),
            groupby='account_id',
        )
        test_line_8 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10.20'),
            groupby='account_id',
        )
        test_line_9 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10.20 - 101 + 101002'),
            groupby='account_id',
        )
        test_line_10 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'10.20 - 101\(101002)'),
            groupby='account_id',
        )
        test_line_11 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'345D\()D'),
            groupby='account_id',
        )
        test_line_12 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'345D\()C'),
            groupby='account_id',
        )

        report = self._create_report([
            test_line_1, test_line_2, test_line_3, test_line_4, test_line_5, test_line_6, test_line_7, test_line_8,
            test_line_9, test_line_10, test_line_11, test_line_12,
        ])

        # Create the journal entries.
        move = self._create_test_account_moves([
            self._prepare_test_account_move_line(1000.0, account_code='100001'),
            self._prepare_test_account_move_line(2000.0, account_code='101001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(-600.0, account_code='101003'),
            self._prepare_test_account_move_line(10000.0, account_code='10.20.0'),
            self._prepare_test_account_move_line(10.0, account_code='345D'),
        ])

        # Check the values.
        options = self._generate_options(report, '2020-01-01', '2020-01-01', default_options={'unfold_all': True})
        report_lines = report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',       12100.0),
                ('10.20.0 10.20.0',   10000.0),
                ('100001 100001',      1000.0),
                ('101001 101001',      2000.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('test_line_2',        -900.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('test_line_3',       13000.0),
                ('10.20.0 10.20.0',   10000.0),
                ('100001 100001',      1000.0),
                ('101001 101001',      2000.0),
                ('test_line_4',       -1700.0),
                ('101001 101001',     -2000.0),
                ('101002 101002',       300.0),
                ('test_line_5',         300.0),
                ('101002 101002',       300.0),
                ('test_line_6',       -2000.0),
                ('101001 101001',     -2000.0),
                ('test_line_7',       10000.0),
                ('10.20.0 10.20.0',   10000.0),
                ('test_line_8',       10000.0),
                ('10.20.0 10.20.0',   10000.0),
                ('test_line_9',        8600.0),
                ('10.20.0 10.20.0',   10000.0),
                ('101001 101001',     -2000.0),
                ('101002 101002',      -300.0),
                ('101003 101003',       600.0),
                ('test_line_10',       8600.0),
                ('10.20.0 10.20.0',   10000.0),
                ('101001 101001',     -2000.0),
                ('101003 101003',       600.0),
                ('test_line_11',         10.0),
                ('345D 345D',            10.0),
                ('test_line_12',           ''),
            ],
        )

        # Check redirection.
        expected_redirection_values_list = [
            move.line_ids[:5],
            move.line_ids[:5],
            move.line_ids[:5],
            move.line_ids[1:3],
            move.line_ids[1:3],
            move.line_ids[1],
            move.line_ids[4],
            move.line_ids[4],
            move.line_ids[1:5],
            move.line_ids[1] + move.line_ids[3:5],
            move.line_ids[5],
            move.line_ids[5],
        ]
        for report_line, expected_amls in zip(report.line_ids, expected_redirection_values_list):
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(move.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_external(self):
        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_external('sum', [
                self._prepare_test_external_values(100.0, '2020-01-02'),
                self._prepare_test_external_values(200.0, '2020-01-03'),
                self._prepare_test_external_values(300.0, '2020-01-03'),
                self._prepare_test_external_values(299.999999999, '2020-01-05'),
            ])
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_external('most_recent', [
                self._prepare_test_external_values(100.0, '2020-01-02'),
                self._prepare_test_external_values(200.0, '2020-01-03'),
                self._prepare_test_external_values(300.0, '2020-01-03'),
                self._prepare_test_external_values(299.999999999, '2020-01-05'),
            ])
        )
        report = self._create_report([test_line_1, test_line_2])

        # Check the values at multiple dates.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',            ''),
                ('test_line_2',            ''),
            ],
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-02')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',         100.0),
                ('test_line_2',         100.0),
            ],
        )

        options = self._generate_options(report, '2020-01-03', '2020-01-03')
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',         500.0),
                ('test_line_2',         500.0),
            ],
        )

        # Check redirection.
        for report_line, report_line_dict in zip(report.line_ids, report_lines):
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertRecordValues(
                    self.env['account.report.external.value'].search(action_dict['domain']),
                    [
                        {'date': fields.Date.from_string('2020-01-03')},
                        {'date': fields.Date.from_string('2020-01-03')},
                    ],
                )

        options = self._generate_options(report, '2020-01-04', '2020-01-04')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',            ''),
                ('test_line_2',            ''),
            ],
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-04')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          600.0),
                ('test_line_2',          500.0),
            ],
        )

        # Check redirection.
        expected_redirection_values_list = [
            [
                {'date': fields.Date.from_string('2020-01-02')},
                {'date': fields.Date.from_string('2020-01-03')},
                {'date': fields.Date.from_string('2020-01-03')},
            ],
            [
                {'date': fields.Date.from_string('2020-01-03')},
                {'date': fields.Date.from_string('2020-01-03')},
            ],
        ]
        for report_line, report_line_dict, expected_values in zip(report.line_ids, report_lines, expected_redirection_values_list):
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertRecordValues(
                    self.env['account.report.external.value'].search(action_dict['domain']),
                    expected_values,
                )

        options = self._generate_options(report, '2020-01-03', '2020-01-05')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          800.0),
                ('test_line_2',          300.0),
            ],
        )

    def test_engine_custom(self):
        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_custom('_custom_engine_test', subformula='sum'),
            groupby='account_id',
        )
        report = self._create_report([test_line_1])

        # Create the journal entries.
        self._create_test_account_moves([
            self._prepare_test_account_move_line(2000.0, account_code='101001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
        ])

        # Check the values.

        def _custom_engine_test(expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
            domain = [('account_id.code', '=', '101002')]
            domain_key = str(domain)
            formulas_dict = {domain_key: expressions}
            domain_result = report._compute_formula_batch_with_engine_domain(
                options, date_scope, formulas_dict, current_groupby, next_groupby,
                offset=offset, limit=limit,
            )
            return list(domain_result.values())[0]

        orig_get_custom_report_function = report._get_custom_report_function

        def get_custom_report_function(_report, function_name, prefix):
            if function_name == '_custom_engine_test':
                return _custom_engine_test
            return orig_get_custom_report_function(function_name, prefix)

        with patch.object(type(report), '_get_custom_report_function', get_custom_report_function):
            options = self._generate_options(report, '2020-01-01', '2020-01-01')
            self.assertLinesValues(
                # pylint: disable=bad-whitespace
                report._get_lines(options),
                [   0,                          1],
                [
                    ('test_line_1',        -300.0),
                    ('101002 101002',      -300.0),
                ],
            )

    def test_engine_aggregation(self):
        self.env.company.account_fiscal_country_id = self.fake_country
        self.currency_data['currency'].name = 'GOL'

        # Test division by zero.
        test1 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('11', label='tax_tags'),
            self._prepare_test_expression_domain([('account_id.code', '=', '101002')], 'sum', label='domain'),
            self._prepare_test_expression_external('sum', [self._prepare_test_external_values(100.0, '2020-01-01')], label='external'),
            self._prepare_test_expression_aggregation('test1.tax_tags / 0'),
            name='test1', code='test1',
        )

        # Test if_(above|below|between) operators.
        test2_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(USD(0))'),
            name='test2_1', code='test2_1',
        )
        test2_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(USD(1999.9999999))'),
            name='test2_2', code='test2_2',
        )
        test2_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(USD(2500.0))'),
            name='test2_3', code='test2_3',
        )
        test2_4 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(GOL(3600.0))'),
            name='test2_4', code='test2_4',
        )
        test3_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain', subformula='if_below(USD(0))'),
            name='test3_1', code='test3_1',
        )
        test3_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain', subformula='if_below(USD(-300.00001))'),
            name='test3_2', code='test3_2',
        )
        test3_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain', subformula='if_below(USD(- 350))'),
            name='test3_3', code='test3_3',
        )
        test4_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags + test1.domain', subformula='if_between(USD(0), USD(2000))'),
            name='test4_1', code='test4_1',
        )
        test4_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags + test1.domain', subformula='if_between(GOL(0), GOL(3000))'),
            name='test4_2', code='test4_2',
        )

        # Test line code recognition.
        test5 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('101003', label='account_codes'),
            self._prepare_test_expression_aggregation('test1.tax_tags + 9999.account_codes'),
            name='9999', code='9999',
        )

        # Test mathematical operators.
        test6 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation(
                '(test1.tax_tags + (2 * test1.domain) + 100.0) / (9999.account_codes)'
            ),
            name='test6', code='test6',
        )

        # Test other date scope
        test7 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(
                [('account_id.code', '=', '101002')],
                'sum',
                label='domain',
                date_scope='to_beginning_of_period',
            ),
            self._prepare_test_expression_aggregation('test7.domain'),
            name='test7', code='test7',
        )

        report = self._create_report(
            [test1, test2_1, test2_2, test2_3, test2_4, test3_1, test3_2, test3_3, test4_1, test4_2, test5, test6, test7],
            country_id=self.fake_country.id,
        )

        # Create the journal entries.
        moves = self._create_test_account_moves([
            self._prepare_test_account_move_line(100000.0, account_code='101002', date='2019-01-01'),
            self._prepare_test_account_move_line(2000.0, account_code='101001', tax_tags=['+11']),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(1500.0, account_code='101003'),
        ])

        # Check the values.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test1',                  ''),
                ('test2_1',            2000.0),
                ('test2_2',                ''),
                ('test2_3',                ''),
                ('test2_4',            2000.0),
                ('test3_1',            -300.0),
                ('test3_2',                ''),
                ('test3_3',                ''),
                ('test4_1',            1700.0),
                ('test4_2',                ''),
                ('9999',               3500.0),
                ('test6',                 1.0),
                ('test7',            100000.0),
            ],
        )

        # Check redirection.
        expected_amls_to_test = [
            ('9999', moves[1].line_ids[0] + moves[1].line_ids[2]),
            ('test7', moves[0].line_ids[0]),
        ]
        for report_line_name, expected_amls in expected_amls_to_test:
            report_line = report.line_ids.filtered(lambda x: x.name == report_line_name)
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(moves.line_ids.filtered_domain(action_dict['domain']), expected_amls)
