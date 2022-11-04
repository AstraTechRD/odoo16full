# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, _
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

class BankReconciliationReportCustomHandler(models.AbstractModel):
    _name = 'account.bank.reconciliation.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Bank Reconciliation Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        print_mode = self._context.get('print_mode')
        journal_id = options.get('bank_reconciliation_report_journal_id')

        if journal_id is None:
            return []

        journal = self.env['account.journal'].browse(journal_id)
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency

        # === Warnings ====

        # Inconsistent statements.
        options['inconsistent_statement_ids'] = self._get_inconsistent_statements(options, journal).ids

        # Strange miscellaneous journal items affecting the bank accounts.
        domain = self._get_bank_miscellaneous_move_lines_domain(options, journal)
        if domain:
            options['has_bank_miscellaneous_move_lines'] = bool(self.env['account.move.line'].search_count(domain))
        else:
            options['has_bank_miscellaneous_move_lines'] = False
        options['account_names'] = journal.default_account_id.display_name

        # ==== Build sub-sections about journal items ====

        plus_st_lines, less_st_lines = self._get_statement_report_lines(report, options, journal)
        plus_pay_lines, less_pay_lines = self._get_payment_report_lines(report, options, journal)

        # ==== Build section block about statement lines ====

        reference_cells = {}
        balance_cells = {}
        column_values = {}
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            domain = report._get_options_domain(column_group_options, 'normal')
            balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]

            last_statement_domain = [('date', '<=', column_group_options['date']['date_to'])]
            if not column_group_options['all_entries']:
                last_statement_domain.append(('move_id.state', '=', 'posted'))
            last_statement = journal._get_last_bank_statement(domain=last_statement_domain)

            # Compute the 'Reference' cell.
            if last_statement and not print_mode:
                reference_cells[column_group_key] = {
                    'last_statement_name': last_statement.display_name,
                    'last_statement_id': last_statement.id,
                    'template': 'account_reports.bank_reconciliation_report_cell_template_link_last_statement',
                    'style': 'white-space: nowrap;',
                }
            else:
                reference_cells[column_group_key] = {}

            # Compute the 'Amount' cell.
            balance_cells[column_group_key] = {
                'name': report.format_value(balance_gl, currency=report_currency, figure_type='monetary'),
                'balance': balance_gl,
                'class': 'number',
            }
            if last_statement:
                report_date = fields.Date.from_string(options['date']['date_to'])
                lines_before_date_to = last_statement.line_ids.filtered(lambda line: line.date <= report_date)
                balance_end = last_statement.balance_start + sum(lines_before_date_to.mapped('amount'))
                difference = balance_gl - balance_end

                if not report_currency.is_zero(difference):
                    balance_cells[column_group_key].update({
                        'template': 'account_reports.bank_reconciliation_report_cell_template_unexplained_difference',
                        'style': 'color:orange; white-space: nowrap;',
                        'title': _(
                            "The current balance in the General Ledger %s doesn't match the balance of your last bank statement %s leading "
                            "to an unexplained difference of %s.",
                             balance_cells[column_group_key]['name'],
                             report.format_value(balance_end, currency=report_currency, figure_type='monetary'),
                             report.format_value(difference, currency=report_currency, figure_type='monetary'),
                         ),
                    })

            column_values[column_group_key] = {
                'date': {'name': format_date(self.env, column_group_options['date']['date_to']), 'class': 'date'},
                'label': reference_cells[column_group_key],
                'amount': balance_cells[column_group_key],
            }

        balance_gl_report_line = {
            'id': report._get_generic_line_id(None, None, markup='balance_gl_line'),
            'name': _("Balance of %s", options['account_names']),
            'title_hover': _("The Book balance in Odoo dated today"),
            'columns': [
                column_values.get(column['column_group_key']).get(column['expression_label'], {})
                for column in options['columns']
            ],
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 0,
            'unfolded': True,
            'unfoldable': False,
        }

        section_st_report_lines = [(0, balance_gl_report_line)] + plus_st_lines + less_st_lines

        if self.env.company.totals_below_sections:
            section_st_report_lines.append((0, {
                'id': report._get_generic_line_id(None, None, markup='total', parent_line_id=balance_gl_report_line['id']),
                'parent_id': balance_gl_report_line['id'],
                'name': _("Total %s", balance_gl_report_line['name']),
                'columns': balance_gl_report_line['columns'],
                'class': 'total',
                'level': balance_gl_report_line['level'] + 1,
            }))

        # ==== Build section block about payments ====

        section_pay_report_lines = []

        if plus_pay_lines or less_pay_lines:

            # Compute totals to display for each section column.
            totals = {}
            for i, column_data in enumerate(options['columns']):
                if column_data['expression_label'] == 'amount':
                    totals.setdefault(column_data['column_group_key'], 0.0)
                    if plus_pay_lines:
                        totals[column_data['column_group_key']] += plus_pay_lines[0][1]['columns'][i]['no_format']
                    if less_pay_lines:
                        totals[column_data['column_group_key']] += less_pay_lines[0][1]['columns'][i]['no_format']

            outstanding_payments_report_line = {
                'id': report._get_generic_line_id(None, None, markup='outstanding_payments'),
                'name': _("Outstanding Payments/Receipts"),
                'title_hover': _("Transactions that were entered into Odoo, but not yet reconciled (Payments triggered by invoices/bills or manually)"),
                'columns': [
                    {
                        'name': report.format_value(totals.get(column['column_group_key']), currency=report_currency, figure_type='monetary'),
                        'no_format': totals.get(column['column_group_key']),
                        'class': 'number',
                    }
                    if column['expression_label'] == 'amount' else {}
                    for column in options['columns']
                ],
                'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
                'level': 0,
                'unfolded': True,
                'unfoldable': False,
            }
            section_pay_report_lines += [(0, outstanding_payments_report_line)] + plus_pay_lines + less_pay_lines

            if self.env.company.totals_below_sections:
                section_pay_report_lines.append((0, {
                    'id': report._get_generic_line_id(None, None, markup='total', parent_line_id=outstanding_payments_report_line['id']),
                    'parent_id': outstanding_payments_report_line['id'],
                    'name': _("Total %s", outstanding_payments_report_line['name']),
                    'columns': outstanding_payments_report_line['columns'],
                    'class': 'total',
                    'level': outstanding_payments_report_line['level'] + 1,
                }))

        # ==== Build trailing section block ====

        return section_st_report_lines + section_pay_report_lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if 'active_id' in self._context and self._context.get('active_model') == 'account.journal':
            options['bank_reconciliation_report_journal_id'] = self._context['active_id']
        elif previous_options and 'bank_reconciliation_report_journal_id' in previous_options:
            options['bank_reconciliation_report_journal_id'] = previous_options['bank_reconciliation_report_journal_id']
        # Remove multi-currency columns if needed
        is_multi_currency = report.user_has_groups('base.group_multi_currency') and report.user_has_groups('base.group_no_one')
        if not is_multi_currency:
            options['columns'] = [
                column for column in options['columns']
                if column['expression_label'] not in ('amount_currency', 'currency')
            ]

    def _get_inconsistent_statements(self, options, journal):
        ''' Retrieve the account.bank.statements records on the range of the options date having different starting
        balance regarding its previous statement.
        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        An account.bank.statements recordset.
        '''
        return self.env['account.bank.statement'].search([
            ('journal_id', '=', journal.id),
            ('date', '<=', options['date']['date_to']),
            ('is_complete', '=', False),
        ])

    def _get_bank_miscellaneous_move_lines_domain(self, options, journal):
        ''' Get the domain to be used to retrieve the journal items affecting the bank accounts but not linked to
        a statement line.
        :param options: The report options.
        :param journal: The account.journal from which this report has been opened.
        :return:        A domain to search on the account.move.line model.
        '''

        if not journal.default_account_id:
            return None

        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
            ('account_id', '=', journal.default_account_id.id),
            ('statement_line_id', '=', False),
            ('date', '<=', options['date']['date_to']),
        ]

        if not options['all_entries']:
            domain.append(('move_id.state', '=', 'posted'))

        if journal.company_id.account_opening_move_id:
            domain.append(('move_id', '!=', journal.company_id.account_opening_move_id.id))

        return domain

    # -------------------------------------------------------------------------
    # COLUMNS / LINES
    # -------------------------------------------------------------------------

    def _build_section_report_lines(self, report, options, journal, unfolded_lines, totals, title, title_hover):
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        report_lines = []

        if not unfolded_lines:
            return report_lines

        line_id = unfolded_lines[0][1]['parent_id']
        is_unfolded = unfold_all or line_id in options['unfolded_lines']

        section_report_line = {
            'id': line_id,
            'name': title,
            'title_hover': title_hover,
            'columns': [
                {
                    'name': report.format_value(totals.get(column['column_group_key']), currency=report_currency, figure_type='monetary'),
                    'no_format': totals.get(column['column_group_key']),
                    'class': 'number',
                }
                if column['expression_label'] == 'amount' else {}
                for column in options['columns']
            ],
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'level': 1,
            'unfolded': is_unfolded,
            'unfoldable': True,
        }
        report_lines += [(0, section_report_line)] + unfolded_lines

        return report_lines

    def _get_statement_report_lines(self, report, options, journal):
        ''' Retrieve the journal items used by the statement lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        if not journal.default_account_id:
            return [], []

        plus_report_lines = []
        less_report_lines = []
        plus_totals = {column['column_group_key']: 0.0 for column in options['columns']}
        less_totals = {column['column_group_key']: 0.0 for column in options['columns']}

        grouped_results = {}
        query, params = self._get_statement_lines_query(report, options, journal)
        self._cr.execute(query, params)

        for results in self._cr.dictfetchall():
            grouped_results.setdefault(results['id'], {})[results['column_group_key']] = results

        for st_line_id, column_group_results in grouped_results.items():

            columns = []
            line_amounts = {}
            move_name = None
            st_line_id = None

            for column in options['columns']:

                col_expr_label = column['expression_label']
                results = column_group_results.get(column['column_group_key'], {})
                line_amounts[column['column_group_key']] = 0.0

                if col_expr_label == 'label':
                    col_value = results and report._format_aml_name(results['payment_ref'], results['ref'], '/') or None
                else:
                    col_value = results.get(col_expr_label)

                if col_value is None:
                    columns.append({})
                else:
                    reconcile_rate = abs(results['suspense_balance']) / (abs(results['suspense_balance']) + abs(results['other_balance']))
                    move_name = move_name or results['name']
                    st_line_id = st_line_id or results['id']
                    col_class = ''
                    if col_expr_label == 'amount_currency':
                        col_value = results['amount_currency'] * reconcile_rate
                        col_class = 'number'
                        foreign_currency = self.env['res.currency'].browse(results['foreign_currency_id'])
                        formatted_value = report.format_value(col_value, currency=foreign_currency, figure_type=column['figure_type'])
                    elif col_expr_label == 'amount':
                        col_value *= reconcile_rate
                        col_class = 'number'
                        formatted_value = report.format_value(col_value, currency=report_currency, figure_type=column['figure_type'])
                        line_amounts[column['column_group_key']] += col_value
                        if col_value >= 0:
                            plus_totals[column['column_group_key']] += col_value
                        else:
                            less_totals[column['column_group_key']] += col_value
                    elif col_expr_label == 'date':
                        col_class = 'date'
                        formatted_value = format_date(self.env, col_value)
                    else:
                        formatted_value = report.format_value(col_value, figure_type=column['figure_type'])

                    columns.append({
                        'name': formatted_value,
                        'no_format': col_value,
                        'class': col_class,
                    })

            st_report_line = {
                'name': move_name,
                'columns': columns,
                'model': 'account.bank.statement.line',
                'caret_options': 'account.bank.statement',
                'level': 3,
            }

            # Only one of the values will be != 0, so the sum() will just return the not null value
            line_amount = sum(line_amounts.values())
            if line_amount > 0.0:
                st_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='plus_unreconciled_statement_lines'
                )
                plus_report_lines.append((0, st_report_line))
            else:
                st_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='less_unreconciled_statement_lines'
                )
                less_report_lines.append((0, st_report_line))
            st_report_line['id'] = report._get_generic_line_id(
                'account.bank.statement.line', st_line_id,
                parent_line_id=st_report_line['parent_id']
            )

            is_parent_unfolded = unfold_all or st_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                st_report_line['style'] = 'display: none;'

        return (
            self._build_section_report_lines(report, options, journal, plus_report_lines, plus_totals,
                _("Including Unreconciled Bank Statement Receipts"),
                _("%s for Transactions(+) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
            self._build_section_report_lines(report, options, journal, less_report_lines, less_totals,
                _("Including Unreconciled Bank Statement Payments"),
                _("%s for Transactions(-) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
        )

    def _get_statement_lines_query(self, report, options, journal):
        queries = []
        params = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():

            tables, where_clause, where_params = report._query_get(column_group_options, 'strict_range', domain=[
                ('journal_id', '=', journal.id),
                ('account_id', '!=', journal.default_account_id.id),
            ])

            queries.append(f'''
                (SELECT
                    %s AS column_group_key,
                    st_line.id,
                    move.name,
                    move.ref,
                    move.date,
                    st_line.payment_ref,
                    st_line.amount,
                    st_line.amount_currency,
                    st_line.foreign_currency_id,
                    res_currency.name AS currency,
                    COALESCE(SUM(CASE WHEN account_move_line.account_id = %s THEN account_move_line.balance ELSE 0.0 END), 0.0) AS suspense_balance,
                    COALESCE(SUM(CASE WHEN account_move_line.account_id = %s THEN 0.0 ELSE account_move_line.balance END), 0.0) AS other_balance
                FROM {tables}
                JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
                JOIN account_move move ON move.id = st_line.move_id
                LEFT JOIN res_currency ON res_currency.id = st_line.foreign_currency_id
                WHERE {where_clause}
                    AND NOT st_line.is_reconciled
                GROUP BY
                    st_line.id,
                    move.name,
                    move.ref,
                    move.date,
                    st_line.amount,
                    st_line.amount_currency,
                    st_line.foreign_currency_id,
                    res_currency.name
                ORDER BY st_line.statement_id DESC, move.date, st_line.sequence, st_line.id DESC)
            ''')
            params += [column_group_key, journal.suspense_account_id.id, journal.suspense_account_id.id, *where_params]

        return ' UNION ALL '.join(queries), params

    def _get_payment_report_lines(self, report, options, journal):
        ''' Retrieve the journal items used by the payment lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        accounts = journal._get_journal_inbound_outstanding_payment_accounts() \
                   + journal._get_journal_outbound_outstanding_payment_accounts()
        if not accounts:
            return [], []

        # Allow user managing payments without any statement lines.
        # In that case, the user manages transactions only using the register payment wizard.
        if journal.default_account_id in accounts:
            return [], []

        plus_report_lines = []
        less_report_lines = []
        plus_totals = {column['column_group_key']: 0.0 for column in options['columns']}
        less_totals = {column['column_group_key']: 0.0 for column in options['columns']}

        grouped_results = {}
        query, params = self._get_payment_query(report, options, accounts, journal)
        self._cr.execute(query, params)

        for results in self._cr.dictfetchall():
            grouped_results.setdefault(results['payment_id'], {}).setdefault(results['column_group_key'], results)

        for column_group_results in grouped_results.values():

            columns = []
            line_amounts = {}
            move_name = None
            move_id = None
            account_id = None
            payment_id = None

            for column in options['columns']:

                col_expr_label = column['expression_label']
                results = column_group_results.get(column['column_group_key'], {})
                line_amounts[column['column_group_key']] = 0.0

                if col_expr_label == 'label':
                    col_value = results.get('ref')
                else:
                    col_value = results.get(col_expr_label)

                if col_value is None:
                    columns.append({})
                else:
                    move_name = move_name or results['name']
                    move_id = move_id or results['move_id']
                    account_id = account_id or results['account_id']
                    payment_id = payment_id or results['payment_id']
                    col_class = ''
                    no_convert = journal_currency and results['currency_id'] == journal_currency.id
                    if col_expr_label == 'amount_currency':
                        if no_convert:
                            col_value = 0.0
                        else:
                            foreign_currency = self.env['res.currency'].browse(results['currency_id'])
                            col_value = results['amount_residual_currency'] if results['is_account_reconcile'] else results['amount_currency']
                        col_class = 'number'
                        formatted_value = report.format_value(col_value, currency=foreign_currency, figure_type=column['figure_type'])
                    elif col_expr_label == 'amount':
                        if no_convert:
                            col_value = results['amount_residual_currency'] if results['is_account_reconcile'] else results['amount_currency']
                        else:
                            balance = results['amount'] if results['is_account_reconcile'] else results['balance']
                            col_value = company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to'])
                        col_class = 'number'
                        formatted_value = report.format_value(col_value, currency=journal_currency, figure_type=column['figure_type'])
                        line_amounts[column['column_group_key']] += col_value
                        if col_value >= 0:
                            plus_totals[column['column_group_key']] += col_value
                        else:
                            less_totals[column['column_group_key']] += col_value
                    elif col_expr_label == 'date':
                        col_class = 'date'
                        formatted_value = format_date(self.env, col_value)
                    else:
                        if no_convert:
                            col_value = ''
                        formatted_value = report.format_value(col_value, figure_type=column['figure_type'])

                    columns.append({
                        'name': formatted_value,
                        'no_format': col_value,
                        'class': col_class,
                    })

            model = 'account.payment' if payment_id else 'account.move'
            pay_report_line = {
                'name': move_name,
                'columns': columns,
                'model': model,
                'caret_options': model,
                'level': 3,
            }

            if account_id in journal._get_journal_inbound_outstanding_payment_accounts().ids:
                pay_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='plus_unreconciled_payment_lines'
                )
                plus_report_lines.append((0, pay_report_line))
            else:
                pay_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='less_unreconciled_payment_lines'
                )
                less_report_lines.append((0, pay_report_line))
            pay_report_line['id'] = report._get_generic_line_id(
                model, payment_id or move_id,
                parent_line_id=pay_report_line['parent_id']
            )

            is_parent_unfolded = unfold_all or pay_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                pay_report_line['style'] = 'display: none;'

        return (
            self._build_section_report_lines(report, options, journal, plus_report_lines, plus_totals,
                _("(+) Outstanding Receipts"),
                _("Transactions(+) that were entered into Odoo, but not yet reconciled (Payments triggered by "
                  "invoices/refunds or manually)"),
            ),
            self._build_section_report_lines(report, options, journal, less_report_lines, less_totals,
                _("(-) Outstanding Payments"),
                _("Transactions(-) that were entered into Odoo, but not yet reconciled (Payments triggered by "
                  "bills/credit notes or manually)"),
            ),
        )

    def _get_payment_query(self, report, options, accounts, journal):
        queries = []
        params = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():

            tables, where_clause, where_params = report._query_get(column_group_options, 'normal', domain=[
                ('journal_id', '=', journal.id),
                ('account_id', 'in', accounts.ids),
                ('full_reconcile_id', '=', False),
                ('amount_residual_currency', '!=', 0.0),
            ])

            queries.append(f'''
                (SELECT
                    %s AS column_group_key,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move.id as move_id,
                    account_move_line.currency_id,
                    account_move.name,
                    account_move.ref,
                    account_move.date,
                    account.reconcile AS is_account_reconcile,
                    res_currency.name AS currency,
                    SUM(account_move_line.amount_residual) AS amount,
                    SUM(account_move_line.balance) AS balance,
                    SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                    SUM(account_move_line.amount_currency) AS amount_currency
                FROM {tables}
                JOIN account_move on account_move.id = account_move_line.move_id
                JOIN account_account account ON account.id = account_move_line.account_id
                LEFT JOIN res_currency ON res_currency.id = account_move_line.currency_id
                WHERE {where_clause}
                GROUP BY
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move.id,
                    account_move_line.currency_id,
                    account_move.name,
                    account_move.ref,
                    account_move.date,
                    account.reconcile,
                    res_currency.name
                ORDER BY account_move.date DESC, account_move_line.payment_id DESC)
            ''')
            params += [column_group_key, *where_params]

        return ' UNION ALL '.join(queries), params

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def bank_reconciliation_report_open_inconsistent_statements(self, options, params=None):
        ''' An action opening the account.bank.statement view (form or list) depending the 'inconsistent_statement_ids'
        key set on the options.
        :param options: The report options.
        :param params:  -Not used-.
        :return:        An action redirecting to a view of statements.
        '''
        inconsistent_statement_ids = options.get('inconsistent_statement_ids', [])

        action = {
            'name': _("Inconsistent Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
        }
        if len(inconsistent_statement_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': inconsistent_statement_ids[0],
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'list',
                'domain': [('id', 'in', inconsistent_statement_ids)],
                'views': [(False, 'list')],
            })
        return action

    def open_bank_miscellaneous_move_lines(self, options, params):
        ''' An action opening the account.move.line tree view affecting the bank account balance but not linked to
        a bank statement line.
        :param options: The report options.
        :param params:  -Not used-.
        :return:        An action redirecting to the tree view of journal items.
        '''
        journal = self.env['account.journal'].browse(options['bank_reconciliation_report_journal_id'])

        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_type': 'list',
            'view_mode': 'list',
            'target': 'current',
            'views': [(self.env.ref('account.view_move_line_tree').id, 'list')],
            'domain': self.env['account.bank.reconciliation.report.handler']._get_bank_miscellaneous_move_lines_domain(options, journal),
        }

    def action_redirect_to_bank_statement_widget(self, options, params):
        ''' Redirect the user to the requested bank statement, if empty displays all bank transactions of the journal.
        :param options:     The report options.
        :param params:      The action params containing at least 'statement_id', can be false.
        :return:            A dictionary representing an ir.actions.act_window.
        '''
        last_statement = self.env['account.bank.statement'].browse(params['statement_id'])

        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[
                ('statement_id', '=', last_statement.id),
                ('journal_id', '=', (last_statement.journal_id or self).id)
            ],
            default_context={'create': False},
            name=last_statement.display_name,
        )

