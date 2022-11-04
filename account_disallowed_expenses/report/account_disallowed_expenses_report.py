# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.misc import get_lang


class DisallowedExpensesCustomHandler(models.AbstractModel):
    _name = 'account.disallowed.expenses.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Disallowed Expenses Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        results = self._get_query_results(options, groupby='category_id')
        lines = []

        for category_id in results:
            lines.append((0, self._get_category_line(options, results[category_id], {'category': category_id})))

        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        # Check if there are multiple rates
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        period_domain = [('date_from', '>=', options['date']['date_from']), ('date_from', '<=', options['date']['date_to'])]
        rg = self.env['account.disallowed.expenses.rate']._read_group(period_domain, ['rate'], 'category_id')
        options['multi_rate_in_period'] = any(cat['category_id_count'] > 1 for cat in rg)

    def _get_query(self, options, line_dict_id=None):
        """ Generates all the query elements based on the 'options' and the 'line_dict_id'.
            :param options:         The report options.
            :param line_dict_id:    The generic id of the line being expanded (optional).
            :return:                The query, split into several elements that can be overridden in child reports.
        """
        company_ids = tuple(self.env.companies.ids) if options.get('multi_company', False) else tuple(self.env.company.ids)
        current = self._parse_line_id(line_dict_id)
        params = {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': company_ids,
            'lang': self.env.user.lang or get_lang(self.env).code,
            **current,
        }

        lang = self.env.user.lang or get_lang(self.env).code
        if self.pool['account.account'].name.translate:
            account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')"
        else:
            account_name = 'account.name'

        select = f"""
            SELECT
                %(column_group_key)s AS column_group_key,
                SUM(aml.balance) AS total_amount,
                ARRAY_AGG({account_name}) account_name,
                ARRAY_AGG(account.code) account_code,
                ARRAY_AGG(category.id) category_id,
                ARRAY_AGG(COALESCE(category.name->>'{lang}', category.name->>'en_US')) category_name,
                ARRAY_AGG(category.code) category_code,
                ARRAY_AGG(account.company_id) company_id,
                ARRAY_AGG(aml.account_id) account_id,
                ARRAY_AGG(rate.rate) account_rate,
                SUM(aml.balance * rate.rate) / 100 AS account_disallowed_amount"""

        from_ = """
            FROM account_move_line aml
            JOIN account_move move ON aml.move_id = move.id
            JOIN account_account account ON aml.account_id = account.id
            JOIN account_disallowed_expenses_category category ON account.disallowed_expenses_category_id = category.id
            LEFT JOIN account_disallowed_expenses_rate rate ON rate.id = (
                SELECT r2.id FROM account_disallowed_expenses_rate r2
                LEFT JOIN account_disallowed_expenses_category c2 ON r2.category_id = c2.id
                WHERE r2.date_from <= aml.date
                  AND c2.id = category.id
                ORDER BY r2.date_from DESC LIMIT 1
            )"""
        where = """
            WHERE aml.company_id in %(company_ids)s
              AND aml.date >= %(date_from)s AND aml.date <= %(date_to)s
              AND move.state != 'cancel'"""
        where += current.get('category') and " AND category.id = %(category)s" or ""
        where += current.get('account') and " AND aml.account_id = %(account)s" or ""
        where += current.get('account_rate') and " AND rate.rate = %(account_rate)s" or ""
        where += not options.get('all_entries') and " AND move.state = 'posted'" or ""

        group_by = " GROUP BY category.id, COALESCE(NULLIF(category_tr.value, ''), category.name)"
        group_by += current.get('category') and ", account_id" or ""
        group_by += current.get('account') and options['multi_rate_in_period'] and ", rate.rate" or ""

        order_by = " ORDER BY category_id, account_id"
        order_by_rate = ", account_rate"

        return select, from_, where, group_by, order_by, order_by_rate, params

    def _parse_line_id(self, line_id):
        current = {'category': None}

        if not line_id:
            return current

        for dummy, model, record_id in self.env['account.report']._parse_line_id(line_id):
            if model == 'account.disallowed.expenses.category':
                current['category'] = record_id
            if model == 'account.account':
                current['account'] = record_id
            if model == 'account.disallowed.expenses.rate':
                current['account_rate'] = record_id

        return current

    def _build_line_id(self, current, parent=False):
        report = self.env['account.report']
        parent_line_id = ''
        line_id = report._get_generic_line_id('account.disallowed.expenses.category', current['category'])
        if current.get('account'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.account', current['account'], parent_line_id=line_id)
        if current.get('account_rate'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.disallowed.expenses.rate', current['account_rate'], parent_line_id=line_id)

        return parent_line_id if parent else line_id

    def _get_query_results(self, options, groupby=None, line_dict_id=None):
        grouped_results = {}

        for column_group_key, column_group_options in self.env['account.report']._split_options_per_column_group(options).items():
            select, from_, where, group_by, order_by, order_by_rate, params = self._get_query(column_group_options, line_dict_id)
            params['column_group_key'] = column_group_key
            self.env.cr.execute(select + from_ + where + group_by + order_by + order_by_rate, params)

            for results in self.env.cr.dictfetchall():
                results['rate'] = self._get_current_rate(results)
                results['disallowed_amount'] = self._get_current_disallowed_amount(results)
                groupby = self._check_groupby(groupby, results)
                grouped_results.setdefault(results[groupby][0], {})[column_group_key] = results

        return grouped_results

    def _check_groupby(self, groupby, results):
        # Hook to be overridden.
        return groupby

    def _report_expand_unfoldable_line_category_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        results = self._get_query_results(options, groupby, line_dict_id)
        lines = []

        for account_id, values in results.items():
            current = {
                'category': list(values.values())[0]['category_id'][0],
                'account': account_id,
            }
            lines.append(self._get_account_line(options, results[account_id], current))

        return {'lines': lines}

    def _report_expand_unfoldable_line_account_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        results = self._get_query_results(options, groupby, line_dict_id)
        lines = []

        for rate, values in results.items():
            base_line_values = list(values.values())[0]
            current = {
                'category': base_line_values['category_id'][0],
                'account': base_line_values['account_id'][0],
                'account_rate': rate,
            }
            lines.append(self._get_rate_line(options, results[rate], current))

        return {'lines': lines}

    def _get_column_values(self, options, values):
        column_values = []

        for column in options['columns']:
            col_val = values.get(column['column_group_key'], {}).get(column['expression_label'])

            if not col_val:
                column_values.append({})
            else:
                column_values.append({
                    'name': self.env['account.report'].format_value(col_val, figure_type=column['figure_type']),
                    'no_format': col_val,
                    'class': 'number',
                })

        return column_values

    def _get_category_line(self, options, values, current):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current),
            'name': '%s %s' % (base_line_values['category_code'][0], base_line_values['category_name'][0]),
            'columns': self._get_column_values(options, values),
            'level': len(current),
            'unfoldable': True,
            'expand_function': '_report_expand_unfoldable_line_category_line',
            'groupby': 'account_id',
        }

    def _get_account_line(self, options, values, current):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current),
            'name': '%s %s' % (base_line_values['account_code'][0], base_line_values['account_name'][0]),
            'columns': self._get_column_values(options, values),
            'level': len(current),
            'unfoldable': options['multi_rate_in_period'],
            'caret_options': False if options['multi_rate_in_period'] else 'account.account',
            'account_id': base_line_values['account_id'],
            'expand_function': options['multi_rate_in_period'] and 'disallowed_expenses_account_line_expand_function',
            'groupby': 'rate',
        }

    def _get_rate_line(self, options, values, current):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current),
            'name': f"{base_line_values['account_code'][0]} {base_line_values['account_name'][0]}",
            'columns': self._get_column_values(options, values),
            'level': len(current),
            'unfoldable': False,
            'caret_options': 'account.account',
            'account_id': base_line_values['account_id'],
        }

    def _get_base_line(self, options, current):
        current_line_id = self._build_line_id(current)
        return {
            'id': current_line_id,
            'parent_id': self._build_line_id(current, parent=True),
            'unfolded': current_line_id in options.get('unfolded_lines') or options.get('unfold_all'),
        }

    def _get_single_value(self, values, key):
        return all(values[key][0] == x for x in values[key]) and values[key][0]

    def _get_current_rate(self, values):
        return self._get_single_value(values, 'account_rate') or ''

    def _get_current_disallowed_amount(self, values):
        return values['account_disallowed_amount']
