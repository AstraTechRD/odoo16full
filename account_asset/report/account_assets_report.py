# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import format_date
from itertools import groupby
from collections import defaultdict

MAX_NAME_LENGTH = 50


class AssetReportCustomHandler(models.AbstractModel):
    _name = 'account.asset.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Asset Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        report = self._with_context_company2code2account(report)

        # construct a dictionary:
        #   {(account_id, asset_id): {col_group_key: {expression_label_1: value, expression_label_2: value, ...}}}
        all_asset_ids = set()
        all_lines_data = {}
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            # the lines returned are already sorted by account_id !
            lines_query_results = self._query_lines(column_group_options)
            for account_id, asset_id, cols_by_expr_label in lines_query_results:
                line_id = (account_id, asset_id)
                all_asset_ids.add(asset_id)
                if line_id not in all_lines_data:
                    all_lines_data[line_id] = {column_group_key: []}
                all_lines_data[line_id][column_group_key] = cols_by_expr_label

        column_names = [
            'assets_date_from', 'assets_plus', 'assets_minus', 'assets_date_to', 'depre_date_from',
            'depre_plus', 'depre_minus', 'depre_date_to', 'balance'
        ]
        totals_by_column_group = defaultdict(lambda: dict.fromkeys(column_names, 0.0))

        # Browse all the necessary assets in one go, to minimize the number of queries
        assets_cache = {asset.id: asset for asset in self.env['account.asset'].browse(all_asset_ids)}

        # construct the lines, 1 at a time
        lines = []
        company_currency = self.env.company.currency_id
        for (account_id, asset_id), col_group_totals in all_lines_data.items():
            all_columns = []
            for column_data in options['columns']:
                col_group_key = column_data['column_group_key']
                expr_label = column_data['expression_label']
                if col_group_key not in col_group_totals or expr_label not in col_group_totals[col_group_key]:
                    all_columns.append({})
                    continue

                col_value = col_group_totals[col_group_key][expr_label]
                if col_value is None:
                    all_columns.append({})
                elif column_data['figure_type'] == 'monetary':
                    all_columns.append({
                        'name': report.format_value(col_value, company_currency, figure_type='monetary'),
                        'no_format': col_value,
                    })
                else:
                    all_columns.append({'name': col_value, 'no_format': col_value})

                # add to the total line
                if column_data['figure_type'] == 'monetary':
                    totals_by_column_group[column_data['column_group_key']][column_data['expression_label']] += col_value

            name = assets_cache[asset_id].name
            line = {
                'id': report._get_generic_line_id('account.asset', asset_id),
                'level': 1,
                'name': name,
                'columns': all_columns,
                'unfoldable': False,
                'unfolded': False,
                'caret_options': 'account_asset_line',
                'class': 'o_account_asset_column_contrast',
                'assets_account_id': account_id,
            }
            if len(name) >= MAX_NAME_LENGTH:
                line['title_hover'] = name
            lines.append(line)

        # add the groups by account
        if options['assets_groupby_account']:
            lines = self._group_by_account(report, lines, options)

        # add the total line
        total_columns = []
        for column_data in options['columns']:
            col_value = totals_by_column_group[column_data['column_group_key']].get(column_data['expression_label'])
            if column_data.get('figure_type') == 'monetary':
                total_columns.append({'name': report.format_value(col_value, company_currency, figure_type='monetary')})
            else:
                total_columns.append({})

        lines.append({
            'id': report._get_generic_line_id(None, None, markup='total'),
            'level': 1,
            'class': 'total',
            'name': _('Total'),
            'columns': total_columns,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]

    def _caret_options_initializer(self):
        # Use 'caret_option_open_record_form' defined in account_reports rather than a custom function
        return {
            'account_asset_line': [
                {'name': _("Open Asset"), 'action': 'caret_option_open_record_form'},
            ]
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        column_group_options_map = report._split_options_per_column_group(options)

        for col in options['columns']:
            column_group_options = column_group_options_map[col['column_group_key']]
            # Dynamic naming of columns containing dates
            if col['expression_label'] == 'balance':
                col['name'] = '' # The column label will be displayed in the subheader
            if col['expression_label'] in ['assets_date_from', 'depre_date_from']:
                col['name'] = format_date(self.env, column_group_options['date']['date_from'])
            elif col['expression_label'] in ['assets_date_to', 'depre_date_to']:
                col['name'] = format_date(self.env, column_group_options['date']['date_to'])

        options['custom_columns_subheaders'] = [
            {"name": "Characteristics", "colspan": 4},
            {"name": "Assets", "colspan": 4},
            {"name": "Depreciation", "colspan": 4},
            {"name": "Book Value", "colspan": 1}
        ]

        # Unfold all by default
        options['unfold_all'] = (previous_options or {}).get('unfold_all', True)

        # Group by account by default
        groupby_activated = (previous_options or {}).get('assets_groupby_account', True)
        options['assets_groupby_account'] = groupby_activated
        # If group by account is activated, activate the hierarchy (which will group by account group as well) if
        # the company has at least one account group, otherwise only group by account
        has_account_group = self.env['account.group'].search_count([('company_id', '=', self.env.company.id)], limit=1)
        options['hierarchy'] = has_account_group and groupby_activated or False

    def _with_context_company2code2account(self, report):
        if self.env.context.get('company2code2account') is not None:
            return report

        company2code2account = defaultdict(dict)
        for account in self.env['account.account'].search([]):
            company2code2account[account.company_id.id][account.code] = account

        return report.with_context(company2code2account=company2code2account)

    def _query_lines(self, options):
        """
        Returns a list of tuples: [(asset_id, account_id, [{expression_label: value}])]
        """
        lines = []
        asset_lines = self._query_values(options)

        # Assign the gross increases sub assets to their main asset (parent)
        parent_lines = []
        children_lines = defaultdict(list)
        for al in asset_lines:
            if al['parent_id']:
                children_lines[al['parent_id']] += [al]
            else:
                parent_lines += [al]

        for al in parent_lines:
            # Compute the depreciation rate string
            if al['asset_method'] == 'linear' and al['asset_method_number']:  # some assets might have 0 depreciations because they dont lose value
                total_months = int(al['asset_method_number']) * int(al['asset_method_period'])
                months = total_months % 12
                years = total_months // 12
                asset_depreciation_rate = " ".join(part for part in [
                    years and _("%s y", years),
                    months and _("%s m", months),
                ] if part)
            elif al['asset_method'] == 'linear':
                asset_depreciation_rate = '0.00 %'
            else:
                asset_depreciation_rate = ('{:.2f} %').format(float(al['asset_method_progress_factor']) * 100)

            # Manage the opening of the asset
            opening = (al['asset_acquisition_date'] or al['asset_date']) < fields.Date.to_date(options['date']['date_from'])

            # Get the main values of the board for the asset
            depreciation_opening = al['depreciated_before']
            depreciation_add = al['depreciated_during']
            depreciation_minus = 0.0

            asset_opening = al['asset_original_value'] if opening else 0.0
            asset_add = 0.0 if opening else al['asset_original_value']
            asset_minus = 0.0

            # Add the main values of the board for all the sub assets (gross increases)
            for child in children_lines[al['asset_id']]:
                depreciation_opening += child['depreciated_before']
                depreciation_add += child['depreciated_during']

                opening = (child['asset_acquisition_date'] or child['asset_date']) < fields.Date.to_date(options['date']['date_from'])
                asset_opening += child['asset_original_value'] if opening else 0.0
                asset_add += 0.0 if opening else child['asset_original_value']

            # Compute the closing values
            asset_closing = asset_opening + asset_add - asset_minus
            depreciation_closing = depreciation_opening + depreciation_add - depreciation_minus

            # Manage the closing of the asset
            if al['asset_state'] == 'close' and al['asset_disposal_date'] and al['asset_disposal_date'] <= fields.Date.to_date(options['date']['date_to']):
                depreciation_minus += depreciation_closing
                depreciation_closing = 0.0
                asset_minus += asset_closing
                asset_closing = 0.0

            # Manage negative assets (credit notes)
            if al['asset_original_value'] < 0:
                asset_add, asset_minus = -asset_minus, -asset_add
                depreciation_add, depreciation_minus = -depreciation_minus, -depreciation_add

            # Format the data
            columns_by_expr_label = {
                options['columns'][0]['expression_label']: al['asset_acquisition_date'] and format_date(self.env, al['asset_acquisition_date']) or '',  # Characteristics
                options['columns'][1]['expression_label']: al['asset_date'] and format_date(self.env, al['asset_date']) or '',
                options['columns'][2]['expression_label']: (al['asset_method'] == 'linear' and _('Linear')) or (al['asset_method'] == 'degressive' and _('Declining')) or _('Dec. then Straight'),
                options['columns'][3]['expression_label']: asset_depreciation_rate}
            for idx, val in enumerate([
                asset_opening, asset_add, asset_minus, asset_closing,
                depreciation_opening, depreciation_add, depreciation_minus, depreciation_closing,
                asset_closing - depreciation_closing,
            ], start=4):
                columns_by_expr_label.update({options['columns'][idx]['expression_label']: val})
            lines.append((al['account_id'], al['asset_id'], columns_by_expr_label))
        return lines

    def _group_by_account(self, report, lines, options):
        """
        This function adds the grouping lines on top of each group of account.asset
        It iterates over the lines, change the line_id of each line to include the account.account.id and the
        account.asset.id.
        """
        if not lines:
            return lines

        rslt_lines = []
        idx_monetary_columns = [idx_col for idx_col, col in enumerate(options['columns']) if col['figure_type'] == 'monetary']
        # while iterating, we compare the 'parent_account_id' with the 'current_account_id' of each line,
        # and sum the monetary amounts into 'group_total', the lines belonging to the same account.account.id are
        # added to 'group_lines'
        parent_account_id = lines[0].get('assets_account_id')  # get parent id name
        group_total = [0] * len(idx_monetary_columns)
        group_lines = []

        dummy_extra_line = {'id': '-account.account-1', 'columns': [{'name': 0, 'no_format': 0}] * len(options['columns'])}
        for line in lines + [dummy_extra_line]:
            line_amounts = [line['columns'][idx].get('no_format', 0) for idx in idx_monetary_columns]
            current_parent_account_id = line.get('assets_account_id')
            # replace the line['id'] to add the account.account.id
            line['id'] = report._build_line_id([
                (None, 'account.account', current_parent_account_id),
                (None, 'account.asset', report._get_model_info_from_id(line['id'])[-1])
            ])
            # if True, the current lines belongs to another account.account.id, we know the preceding group is complete
            # so we can add the grouping line of the preceding group (corresponding to the parent_account_id).
            if current_parent_account_id != parent_account_id:
                account = self.env['account.account'].browse(parent_account_id)
                columns = []
                for idx_col in range(len(options['columns'])):
                    if idx_col in idx_monetary_columns:
                        tot_val = group_total.pop(0)
                        columns.append({
                            'name': report.format_value(tot_val, self.env.company.currency_id, figure_type='monetary'),
                            'no_format': tot_val
                        })
                    else:
                        columns.append({})
                new_line = {
                    'id': report._build_line_id([(None, 'account.account', parent_account_id)]),
                    'name': f"{account.code} {account.name}",
                    'unfoldable': True,
                    'unfolded': options.get('unfold_all', False),
                    'level': 1,
                    'columns': columns,
                    'class': 'o_account_asset_column_contrast',
                }
                rslt_lines += [new_line] + group_lines
                # Reset the control variables
                parent_account_id = current_parent_account_id
                group_total = [0] * len(idx_monetary_columns)
                group_lines = []
            # Add the line amount to the current group_total, set the line's parent_id and add the line to the
            # current group of lines
            group_total = [x + y for x, y in zip(group_total, line_amounts)]
            line['parent_id'] = report._build_line_id([(None, 'account.account', parent_account_id)])
            group_lines.append(line)
        return rslt_lines

    def _query_values(self, options):
        "Get the data from the database"

        self.env['account.move.line'].check_access_rights('read')
        self.env['account.asset'].check_access_rights('read')

        sql = f"""
            SELECT asset.id AS asset_id,
                   asset.parent_id AS parent_id,
                   asset.name AS asset_name,
                   asset.original_value AS asset_original_value,
                   asset.currency_id AS asset_currency_id,
                   asset.acquisition_date AS asset_date,
                   asset.disposal_date AS asset_disposal_date,
                   asset.acquisition_date AS asset_acquisition_date,
                   asset.method AS asset_method,
                   asset.method_number AS asset_method_number,
                   asset.method_period AS asset_method_period,
                   asset.method_progress_factor AS asset_method_progress_factor,
                   asset.state AS asset_state,
                   account.code AS account_code,
                   account.name AS account_name,
                   account.id AS account_id,
                   account.company_id AS company_id,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date < %(date_from)s), 0) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s), 0) AS depreciated_during,
                   COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date > %(date_to)s), 0) AS remaining
              FROM account_asset AS asset
         LEFT JOIN account_account AS account ON asset.account_asset_id = account.id
         LEFT JOIN account_move move ON move.asset_id = asset.id
         LEFT JOIN account_move reversal ON reversal.reversed_entry_id = move.id
             WHERE asset.company_id in %(company_ids)s
               AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
               AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
               AND asset.state not in ('model', 'draft', 'cancelled')
               AND asset.asset_type = 'purchase'
               AND asset.active = 't'
               AND move.state {"!= 'cancel'" if options.get('all_entries') else "= 'posted'"}
               AND reversal.id IS NULL
          GROUP BY asset.id, account.id
          ORDER BY account.code, asset.acquisition_date;
        """

        if options.get('multi_company', False):
            company_ids = tuple(self.env.companies.ids)
        else:
            company_ids = tuple(self.env.company.ids)

        self._cr.execute(sql, {
            'date_to': options['date']['date_to'],
            'date_from': options['date']['date_from'],
            'company_ids': company_ids,
        })
        results = self._cr.dictfetchall()
        return results


class AssetsReport(models.Model):
    _inherit = 'account.report'

    def _get_caret_option_view_map(self):
        view_map = super()._get_caret_option_view_map()
        view_map['account.asset.line'] = 'account_asset.view_account_asset_expense_form'
        return view_map
