# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DisallowedExpensesFleetCustomHandler(models.AbstractModel):
    _name = 'account.disallowed.expenses.fleet.report.handler'
    _inherit = 'account.disallowed.expenses.report.handler'
    _description = 'Disallowed Expenses Fleet Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Initialize vehicle_split filter
        options['vehicle_split'] = previous_options.get('vehicle_split', False)
        if not options.get('vehicle_split'):
            return options

        # Check if there are multiple rates
        period_domain = [('date_from', '>=', options['date']['date_from']), ('date_from', '<=', options['date']['date_to'])]
        rg = self.env['fleet.disallowed.expenses.rate']._read_group(period_domain, ['rate'], 'vehicle_id')
        options['multi_rate_in_period'] = options.get('multi_rate_in_period') or any(cat['vehicle_id_count'] > 1 for cat in rg)

    def _get_query(self, options, line_dict_id=None):
        select, from_, where, group_by, order_by, order_by_rate, params = super()._get_query(options, line_dict_id)
        current = self._parse_line_id(line_dict_id)
        params.update(current)

        select += """,
            ARRAY_AGG(fleet_rate.rate) fleet_rate,
            ARRAY_AGG(vehicle.id) vehicle_id,
            ARRAY_AGG(vehicle.name) vehicle_name,
            SUM(aml.balance * (
                CASE WHEN fleet_rate.rate IS NOT NULL
                THEN fleet_rate.rate
                ELSE rate.rate
                END)) / 100 AS fleet_disallowed_amount
        """
        from_ += """
            LEFT JOIN fleet_vehicle vehicle ON aml.vehicle_id = vehicle.id
            LEFT JOIN fleet_disallowed_expenses_rate fleet_rate ON fleet_rate.id = (
                SELECT r2.id FROm fleet_disallowed_expenses_rate r2
                JOIN fleet_vehicle v2 ON r2.vehicle_id = v2.id
                WHERE r2.date_from <= aml.date
                  AND v2.id = vehicle.id
                ORDER BY r2.date_from DESC LIMIT 1
            )
        """
        where += current.get('vehicle') and """
              AND vehicle.id = %(vehicle)s""" or ""
        where += current.get('account') and not current.get('vehicle') and options.get('vehicle_split') and """
              AND vehicle.id IS NULL""" or ""
        group_by = """
            GROUP BY category.id"""
        group_by += current.get('category') and options.get('vehicle_split') and ", vehicle.id, vehicle.name" or ""
        group_by += current.get('category') and ", account_id" or ""
        group_by += (current.get('account') or current.get('vehicle')) and options['multi_rate_in_period'] and ", rate.rate, fleet_rate.rate" or ""
        order_by = """
            ORDER BY category_id"""
        order_by += current.get('category') and options.get('vehicle_split') and ", vehicle.name IS NOT NULL, vehicle.name" or ""
        order_by += ", account_id"
        order_by_rate += ", fleet_rate"

        return select, from_, where, group_by, order_by, order_by_rate, params

    def _parse_line_id(self, line_id):
        # Override.
        current = {'category': None}

        if not line_id:
            return current

        for dummy, model, record_id in self.env['account.report']._parse_line_id(line_id):
            if model == 'account.disallowed.expenses.category':
                current.update({'category': record_id})
            if model == 'fleet.vehicle':
                current.update({'vehicle': record_id})
            if model == 'account.account':
                current.update({'account': record_id})
            if model == 'account.disallowed.expenses.rate':
                if model == 'fleet.vehicle':
                    current.update({'fleet_rate': record_id})
                else:
                    current.update({'account_rate': record_id})

        return current

    def _build_line_id(self, current, parent=False):
        # Override.
        report = self.env['account.report']
        parent_line_id = ''
        line_id = report._get_generic_line_id('account.disallowed.expenses.category', current['category'])
        if current.get('vehicle'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('fleet.vehicle', current['vehicle'], parent_line_id=line_id)
        if current.get('account'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.account', current['account'], parent_line_id=line_id)
        if current.get('account_rate'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.disallowed.expenses.rate', current['account_rate'], parent_line_id=line_id)
        if current.get('fleet_rate'):
            parent_line_id = line_id
            line_id = report._get_generic_line_id('account.disallowed.expenses.rate', current['fleet_rate'], parent_line_id=line_id)

        return parent_line_id if parent else line_id

    def _check_groupby(self, groupby, results):
        # Override.
        vehicle_id = self._get_single_value(results, 'vehicle_id')
        if vehicle_id:
            if groupby == 'account_id':
                return 'vehicle_id'
            if groupby == 'account_rate':
                return 'fleet_rate'
        else:
            if groupby == 'vehicle_id':
                return 'account_id'
            if groupby == 'fleet_rate':
                return 'account_rate'
        return groupby

    def _report_expand_unfoldable_line_category_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        # Override.
        results = self._get_query_results(options, groupby, line_dict_id)
        lines = []

        for item_id, values in results.items():
            base_line_values = list(values.values())[0]
            category_id = base_line_values['category_id'][0]
            vehicle_id = self._get_single_value(base_line_values, 'vehicle_id')
            if options.get('vehicle_split') and vehicle_id:
                current = {
                    'category': category_id,
                    'vehicle': vehicle_id,
                }
                lines.append(self._disallowed_expenses_get_vehicle_line(options, results[item_id], current))
            else:
                account_id = self._get_single_value(base_line_values, 'account_id')
                current = {
                    'category': category_id,
                    'account': account_id,
                }
                lines.append(self._get_account_line(options, results[item_id], current))

        return {'lines': lines}

    def _report_expand_unfoldable_line_vehicle_line(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        results = self._get_query_results(options, groupby, line_dict_id)
        lines = []

        for rate, values in results.items():
            base_line_values = list(values.values())[0]
            current = {
                'category': base_line_values['category_id'][0],
                'vehicle': base_line_values['vehicle_id'][0],
                'fleet_rate': rate,
            }
            lines.append(self._get_rate_line(options, results[rate], current))

        return {'lines': lines}

    def _disallowed_expenses_get_vehicle_line(self, options, values, current):
        base_line_values = list(values.values())[0]
        return {
            **self._get_base_line(options, current),
            'name': base_line_values['vehicle_name'][0],
            'columns': self._get_column_values(options, values),
            'level': len(current),
            'unfoldable': True,
            'caret_options': False,
            'expand_function': '_report_expand_unfoldable_line_vehicle_line',
            'groupby': 'fleet_rate',
        }

    def _get_current_rate(self, values):
        # Override
        fleet_rate = self._get_single_value(values, 'fleet_rate')
        account_rate = self._get_single_value(values, 'account_rate')

        current_rate = ''
        if fleet_rate is not False:
            if fleet_rate is not None:
                current_rate = fleet_rate
            elif account_rate:
                current_rate = account_rate

        return current_rate

    def _get_current_disallowed_amount(self, values):
        # Override
        return values['fleet_disallowed_amount'] if any(values['vehicle_id']) else values['account_disallowed_amount']
