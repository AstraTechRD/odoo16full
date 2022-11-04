# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from math import floor
from odoo import http, _, fields
from odoo.http import request
from .stat_types import STAT_TYPES, FORECAST_STAT_TYPES, compute_mrr_growth_values


class RevenueKPIsDashboard(http.Controller):

    @http.route('/sale_subscription_dashboard/fetch_data', type='json', auth='user')
    def fetch_data(self):
        dates_ranges = request.env['sale.order']._get_subscription_dates_ranges()
        return {
            'stat_types': {
                key: {
                    'name': stat['name'],
                    'dir': stat['dir'],
                    'code': stat['code'],
                    'tooltip': stat.get('tooltip'),
                    'prior': stat['prior'],
                    'add_symbol': stat['add_symbol'],
                }
                for key, stat in STAT_TYPES.items()
            },
            'forecast_stat_types': {
                key: {
                    'name': stat['name'],
                    'code': stat['code'],
                    'tooltip': stat.get('tooltip'),
                    'prior': stat['prior'],
                    'add_symbol': stat['add_symbol'],
                }
                for key, stat in FORECAST_STAT_TYPES.items()
            },
            'currency_id': request.env.company.currency_id.id,
            'contract_templates': request.env['sale.order.template'].search_read([('recurrence_id', '!=', False)], fields=['name']),
            'companies': request.env['res.company'].search_read([], fields=['name']),
            'has_template': bool(request.env['sale.order.template'].search_count([])),
            'has_mrr': bool(request.env['account.move.line'].search_count([('subscription_start_date', '!=', False)])),
            'sales_team': request.env['crm.team'].search_read([], fields=['name']),
            'dates_ranges': dates_ranges,
        }

    @http.route('/sale_subscription_dashboard/companies_check', type='json', auth='user')
    def companies_check(self, company_ids):
        company_ids = request.env['res.company'].browse(company_ids)
        currency_ids = company_ids.mapped('currency_id')

        if len(currency_ids) == 1:
            return {
                'result': True,
                'currency_id': currency_ids.id,
            }
        elif len(company_ids) == 0:
            message = _('No company selected.')
        elif len(currency_ids) >= 1:
            message = _('It makes no sense to sum MRR of different currencies. Please select companies with the same currency.')
        else:
            message = _('Unknown error')

        return {
            'result': False,
            'error_message': message,
        }

    @http.route('/sale_subscription_dashboard/get_default_values_forecast', type='json', auth='user')
    def get_default_values_forecast(self, forecast_type, end_date, filters):

        end_date = fields.Date.from_string(end_date)

        net_new_mrr = compute_mrr_growth_values(end_date, end_date, filters)['net_new_mrr']
        revenue_churn = self.compute_stat('revenue_churn', end_date, end_date, filters)

        result = {
            'expon_growth': 15,
            'churn': revenue_churn,
            'projection_time': 12,
        }

        if 'mrr' in forecast_type:
            mrr = self.compute_stat('mrr', end_date, end_date, filters)

            result['starting_value'] = mrr
            result['linear_growth'] = net_new_mrr
        else:
            arpu = self.compute_stat('arpu', end_date, end_date, filters)
            nb_contracts = self.compute_stat('nb_contracts', end_date, end_date, filters)

            result['starting_value'] = nb_contracts
            result['linear_growth'] = 0 if arpu == 0 else net_new_mrr/arpu
        return result

    @http.route('/sale_subscription_dashboard/get_stats_history', type='json', auth='user')
    def get_stats_history(self, stat_type, start_date, end_date, filters):

        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)

        results = {}

        for delta in [1, 3, 12]:
            results['value_' + str(delta) + '_months_ago'] = self.compute_stat(
                stat_type,
                start_date - relativedelta(months=+delta),
                end_date - relativedelta(months=+delta),
                filters)

        return results

    @http.route('/sale_subscription_dashboard/get_stats_by_plan', type='json', auth='user')
    def get_stats_by_plan(self, stat_type, start_date, end_date, filters):

        results = []

        domain = [('recurrence_id', '!=', False)]
        if filters.get('template_ids'):
            domain += [('id', 'in', filters.get('template_ids'))]

        template_ids = request.env['sale.order.template'].search(domain)

        for template in template_ids:
            lines_domain = [
                ('subscription_start_date', '<=', end_date),
                ('subscription_end_date', '>=', end_date),
                ('subscription_id.sale_order_template_id', '=', template.id),
            ]
            if filters.get('company_ids'):
                lines_domain.append(('company_id', 'in', filters.get('company_ids')))
            recurring_invoice_line_ids = request.env['account.move.line'].search(lines_domain)
            specific_filters = dict(filters)  # create a copy to modify it
            specific_filters.update({'template_ids': [template.id]})
            value = self.compute_stat(stat_type, start_date, end_date, specific_filters)
            results.append({
                'name': template.name,
                'recurrence': template.recurrence_id.name,
                'nb_customers': len(recurring_invoice_line_ids.mapped('subscription_id')),
                'value': value,
            })

        results = sorted((results), key=lambda k: k['value'], reverse=True)

        return results

    @http.route('/sale_subscription_dashboard/compute_graph_mrr_growth', type='json', auth='user')
    def compute_graph_mrr_growth(self, start_date, end_date, filters, points_limit=0):

        # By default, points_limit = 0 mean every points

        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        delta = end_date - start_date

        ticks = self._get_pruned_tick_values(range(delta.days + 1), points_limit)

        results = defaultdict(list)

        # This is rolling month calculation
        for i in ticks:
            date = start_date + timedelta(days=i)
            date_splitted = str(date).split(' ')[0]

            computed_values = compute_mrr_growth_values(date, date, filters)

            for k in ['new_mrr', 'churned_mrr', 'expansion_mrr', 'down_mrr', 'net_new_mrr']:
                results[k].append({
                    '0': date_splitted,
                    '1': computed_values[k]
                })

        return results

    @http.route('/sale_subscription_dashboard/compute_graph_and_stats', type='json', auth='user')
    def compute_graph_and_stats(self, stat_type, start_date, end_date, filters, points_limit=30):
        """ Returns both the graph and the stats"""

        # This avoids to make 2 RPCs instead of one
        graph = self.compute_graph(stat_type, start_date, end_date, filters, points_limit=points_limit)
        stats = self._compute_stat_trend(stat_type, start_date, end_date, filters)

        return {
            'graph': graph,
            'stats': stats,
        }

    @http.route('/sale_subscription_dashboard/compute_graph', type='json', auth='user')
    def compute_graph(self, stat_type, start_date, end_date, filters, points_limit=30):

        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        delta = end_date - start_date

        ticks = self._get_pruned_tick_values(range(delta.days + 1), points_limit)

        results = []
        for i in ticks:
            # METHOD NON-OPTIMIZED (could optimize it using SQL with generate_series)
            date = start_date + timedelta(days=i)
            value = self.compute_stat(stat_type, date, date, filters)

            # format of results could be changed (we no longer use nvd3)
            results.append({
                '0': str(date).split(' ')[0],
                '1': value,
            })

        return results

    def _compute_stat_trend(self, stat_type, start_date, end_date, filters):

        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        start_date_delta = start_date - relativedelta(months=+1)
        end_date_delta = end_date - relativedelta(months=+1)

        last_month_value = self.compute_stat(stat_type, start_date_delta, end_date_delta, filters)
        current_value = self.compute_stat(stat_type, start_date, end_date, filters)
        perc = 100 if not last_month_value else round(100 * (current_value - last_month_value) / float(last_month_value), 1)
        perc = 0 if not last_month_value and not current_value else perc

        result = {
            'value_1': str(last_month_value),
            'value_2': str(current_value),
            'perc': perc,
        }
        return result

    @http.route('/sale_subscription_dashboard/compute_stat', type='json', auth='user')
    def compute_stat(self, stat_type, start_date, end_date, filters):

        start_date = fields.Date.to_date(start_date)
        end_date = fields.Date.to_date(end_date)

        return STAT_TYPES[stat_type]['compute'](start_date, end_date, filters)

    def _get_pruned_tick_values(self, ticks, nb_desired_ticks):
        if nb_desired_ticks == 0:
            return ticks

        nb_values = len(ticks)
        keep_one_of = max(1, floor(nb_values / float(nb_desired_ticks)))

        ticks = [x for x in ticks if x % keep_one_of == 0]

        return ticks
