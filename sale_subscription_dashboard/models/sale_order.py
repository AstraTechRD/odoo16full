# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import config, date_utils, misc

from itertools import groupby
from operator import itemgetter
from datetime import date
from dateutil.relativedelta import relativedelta
from markupsafe import Markup


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_subscription_dates_ranges(self):
        today = fields.Date.context_today(self)

        is_account_present = hasattr(self.env.company, 'compute_fiscalyear_dates')
        this_year = {'date_from': date(today.year, 1, 1), 'date_to': date(today.year, 12, 31)}
        last_year = {'date_from': date(today.year - 1, 1, 1), 'date_to': date(today.year - 1, 12, 31)}

        this_year_dates = self.env.company.compute_fiscalyear_dates(today) if is_account_present else this_year
        last_year_dates = self.env.company.compute_fiscalyear_dates(today - relativedelta(years=1)) if is_account_present else last_year

        this_quarter_from, this_quarter_to = date_utils.get_quarter(today)
        last_quarter_from, last_quarter_to = date_utils.get_quarter(today - relativedelta(months=3))

        this_month_from, this_month_to = date_utils.get_month(today)
        last_month_from, last_month_to = date_utils.get_month(today - relativedelta(months=1))
        return {
            'this_year': {'date_from': this_year_dates['date_from'], 'date_to': this_year_dates['date_to']},
            'last_year': {'date_from': last_year_dates['date_from'], 'date_to': last_year_dates['date_to']},
            'this_quarter': {'date_from': this_quarter_from, 'date_to': this_quarter_to},
            'last_quarter': {'date_from': last_quarter_from, 'date_to': last_quarter_to},
            'this_month': {'date_from': this_month_from, 'date_to': this_month_to},
            'last_month': {'date_from': last_month_from, 'date_to': last_month_to},
        }

    def _get_salesperson_kpi(self, user_id, start_date, end_date):
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        mrr_res = self._get_salesperson_mrr(user_id, start_date, end_date)
        nrr_res = self._get_salesperson_nrr(user_id, start_date, end_date)

        return {
            'new': mrr_res['new'],
            'churn': mrr_res['churn'],
            'up': mrr_res['up'],
            'down': mrr_res['down'],
            'net_new': mrr_res['net_new'],
            'contract_modifications': mrr_res['contract_modifications'],
            'nrr': nrr_res['nrr'],
            'nrr_invoices': nrr_res['nrr_invoices'],
            'company_ids': mrr_res['company_ids'] + nrr_res['company_ids'],
        }

    def _get_log_type(self, event_type, amount_signed):
        log_type = {'0_creation': 'new', '2_churn': 'churn'}
        if event_type in ['0_creation', '2_churn']:
            return log_type[event_type]
        else:
            if amount_signed > 0:
                return 'up'
            else:
                return 'down'

    def _get_salesperson_mrr(self, user_id, start_date, end_date):
        contract_modifications = []
        domain = [
            ('order_id.user_id', '=', user_id),
            ('event_date', '>=', start_date),
            ('event_date', '<=', end_date),
            ('event_type', '!=', '3_transfer')
        ]
        searched_fields = ['amount_signed', 'create_date', 'company_id', 'currency_id', 'event_type',
                           'event_date', 'id', 'recurring_monthly', 'order_id']
        order_log_ids = self.env['sale.order.log'].search_read(domain, fields=searched_fields, order='order_id')
        order_ids = self.env['sale.order'].browse(set(map(lambda s: s['order_id'][0], order_log_ids)))
        for log in order_log_ids:
            order_id = self.env['sale.order'].browse(log['order_id'][0])
            date = log['event_date']
            currency_id = self.env['res.currency'].browse(log['currency_id'][0])
            recurring_monthly = currency_id._convert(
                from_amount=log['recurring_monthly'], date=date,
                to_currency=self.env.company.currency_id, company=self.env.company)
            amount_signed = currency_id._convert(
                from_amount=log['amount_signed'], date=date,
                to_currency=self.env.company.currency_id, company=self.env.company)
            previous_mrr = recurring_monthly - amount_signed
            contract_modifications.append({'date': date, 'type': self._get_log_type(log['event_type'], log['amount_signed']),
                                           'partner': order_id.partner_id.name,
                                           'subscription': log['order_id'][1], 'code': order_id.name,
                                           'subscription_template': order_id.sale_order_template_id.name,
                                           'previous_mrr': previous_mrr,
                                           'current_mrr': recurring_monthly, 'diff': amount_signed,
                                           'order_id': order_id.id, 'model': 'sale.order',
                                           'event_date': log['event_date'], 'create_date': log['create_date'],
                                           'id': log['id'], 'currency_id': log['currency_id'][0],
                                           'company_id': log['company_id'][0], 'company_name': log['company_id'][1]})
        contracts_clean, metrics = self._contract_modifications_handling(contract_modifications) # cleaning and metrics calculation
        contracts_clean = sorted(contracts_clean, key=itemgetter('code'))
        return {
            'new': metrics['new_mrr'],
            'churn': -metrics['churned_mrr'],
            'up': metrics['expansion_mrr'],
            'down': -metrics['down_mrr'],
            'net_new': metrics['net_new_mrr'],
            'contract_modifications': contracts_clean,
            'company_ids': order_ids.mapped('company_id').ids,
        }

    def _metrics_calculation(self, contract_log):
        metrics_update = {}
        if contract_log.get('type') == 'new':
            metrics_update['new_mrr'] = contract_log['current_mrr']
        elif contract_log.get('type') == 'churn':
            metrics_update['churned_mrr'] = contract_log['previous_mrr']
        elif contract_log.get('type') == 'up':
            metrics_update['expansion_mrr'] = contract_log['diff']
        elif contract_log.get('type') == 'down':
            # force all metrics to be positive at this point
            metrics_update['down_mrr'] = - contract_log['diff']
        return [metrics_update]

    def _contract_modifications_handling(self, contract_modifications):
        graphs_updates_list = [{'new_mrr': 0, 'churned_mrr': 0, 'expansion_mrr': 0, 'down_mrr': 0, 'net_new_mrr': 0}]
        uniques_subscriptions = set([d['order_id'] for d in contract_modifications])
        contract_modifications_clean = []
        for order_id in uniques_subscriptions:
            contracts_logs = [d for d in contract_modifications if d['order_id'] == order_id]
            cleaned_contracts_logs, graphs_update = self._data_cleanup(contracts_logs)
            contract_modifications_clean += cleaned_contracts_logs
            graphs_updates_list += graphs_update
        metrics = {}
        for d in graphs_updates_list:
            for k in d.keys():
                metrics[k] = metrics.get(k, 0) + d[k]
        metrics['net_new_mrr'] = metrics['new_mrr'] - metrics['churned_mrr'] + metrics['expansion_mrr'] - metrics['down_mrr']
        return contract_modifications_clean, metrics

    def _data_cleanup(self, contract_logs):
        """
        This function clean the list of contract modification to make it human readable and clean noisy data.
        Several cases are handled:
            * New subscription upselled or downselled the same day --> One new subscription with the MRR of the upsell
            * New subscriptions cancelled the same day --> Nothing is showed
            * List of ups and down at different dates:
                * When only one creation event for the subscription: all up and down are merged.
                * Subscription is churn and recreated after: up and down are split into date interval to preserve
                  the continuity and coherence of the data. See function`_get_date_intervals`.
        Ideally, the merge should not only occurs for modification the same day but modifications that were too
        close to modify the MRR. It could be done by adapting the date intervals.
        :param contract_logs: list of dictionnary with the contract modifications
        :return: result, a cleaned list of dict
        """
        graphs_update = []
        contract_log_by_date = sorted(contract_logs, key=itemgetter('event_date'))
        scaffold = {'code': None, 'current_mrr': None, 'date': None, 'diff': None, 'model': 'sale.order',
                    'partner': None, 'previous_mrr': None, 'subscription': None, 'order_id': None,
                    'subscription_template': None, 'type': None, 'company_id': None,
                    'company_name': None, 'currency_id': None,
                    }
        result = []
        used_logs = set()
        date_intervals = self._get_date_intervals(contract_log_by_date)
        for date_interval in date_intervals:
            date_start = date_interval[0]
            date_stop = date_interval[1]
            selected_logs_interval = [d for d in contract_log_by_date if date_start <= d['date'] <= date_stop and d['id'] not in used_logs]
            selected_logs_interval = sorted(selected_logs_interval, key=itemgetter('event_date'))
            unique_dates = set([d['date'] for d in selected_logs_interval])
            for date in unique_dates:
                # We identify here the contract log at a precise date
                selected_logs = [d for d in selected_logs_interval if d['date'] == date]
                # Selections are not always sorted by create date
                selected_logs = sorted(selected_logs, key=itemgetter('event_date'))
                n_creation = sum((map(lambda log: log['type'] == 'new', selected_logs)))
                n_churn = sum((map(lambda log: log['type'] == 'churn', selected_logs)))
                event_diff = n_creation - n_churn
                if event_diff:
                    # Contract started or churned.
                    # The data need to be cleaned. We merge it to display a summary.
                    if event_diff > 0:
                        # The contract was started today. We merge all the ups and down of the day.
                        log_type = 'new'
                        previous_mrr = 0
                        current_mrr = float(selected_logs[-1]['current_mrr'])
                        diff = current_mrr
                    else:
                        # The contract was churned today. We merge all the ups and down of the day.
                        log_type = 'churn'
                        current_mrr = 0
                        previous_mrr = float(selected_logs[0]['previous_mrr'])
                        diff = - previous_mrr
                    merged_log = scaffold.copy()
                    for key in scaffold.keys():
                        merged_log[key] = selected_logs[0][key]
                    merged_log['type'] = log_type
                    merged_log['previous_mrr'] = previous_mrr
                    merged_log['current_mrr'] = current_mrr
                    merged_log['diff'] = diff
                    merged_log['create_date'] = selected_logs[-1]['create_date']
                    merged_log['id'] = None
                    graphs_update += self._metrics_calculation(merged_log)
                    result.append(merged_log)
                else:
                    # same amount of create and churn. We do not display anything.
                    continue
                used_logs = used_logs.union(set([d['id'] for d in selected_logs]))
            # Merge the up and down occurring in the date_interval.
            selected_logs = [d for d in contract_log_by_date if
                             d['id'] not in used_logs and date_start <= d['date'] <= date_stop]
            selected_logs = sorted(selected_logs, key=itemgetter('event_date'))
            if selected_logs:
                if len(selected_logs) == 1:
                    graphs_update += self._metrics_calculation(selected_logs[0])
                    result.append(selected_logs[0])
                    used_logs = used_logs.union(set([d['id'] for d in selected_logs]))
                else:
                    # We have more than one MRR change, we want to merge them.
                    merged_log = scaffold.copy()
                    for key in scaffold.keys():
                        merged_log[key] = selected_logs[0][key]
                    merged_log['previous_mrr'] = selected_logs[0]['previous_mrr']
                    merged_log['current_mrr'] = float(selected_logs[-1]['current_mrr'])
                    merged_log['diff'] = merged_log['current_mrr'] - merged_log['previous_mrr']
                    merged_log['create_date'] = selected_logs[-1]['create_date']
                    merged_log['id'] = None
                    if merged_log['diff'] > 0:
                        merged_log['type'] = 'up'
                    else:
                        merged_log['type'] = 'down'
                    if merged_log['diff'] != 0:
                        graphs_update += self._metrics_calculation(merged_log)
                        result.append(merged_log)
                        used_logs = used_logs.union(set([d['id'] for d in selected_logs]))
        result = sorted(result, key=itemgetter('create_date'))
        return result, graphs_update

    def _get_date_intervals(self, contract_log_by_date):
        """
        # When the logs have several create, we need to merge the up and down by date intervals.
        For example if the log sequence is create, up1 down1 churn, create up2 down2, we need to merge
        up1 and down1 together and then up2 with down2 together.
        :param contract_log_by_date: The whole list of contract logs sorted by date.
        :return: a list of date interval: {'start': Datetime, 'stop': Datetime}
        :rtype:
        """
        creations = [d for d in contract_log_by_date if d['type'] == 'new']
        churns = [d for d in contract_log_by_date if d['type'] == 'churn']
        if len(creations) > 1 or len(churns) > 1:
            date_intervals = []
            for idx, creation in enumerate(creations):
                start_date = creation['date']
                try:
                    stop_date = churns[idx]['date']
                except IndexError:
                    stop_date = contract_log_by_date[-1]['date']
                date_intervals.append((start_date, stop_date))
        else:
            # If there is only one create, we can merge the up and down over the whole period.
            date_intervals = [(contract_log_by_date[0]['date'], contract_log_by_date[-1]['date'])]
        return set(date_intervals)

    def _get_salesperson_nrr(self, user_id, start_date, end_date):
        nrr_invoice_ids = []
        total_nrr = 0
        searched_fields = ('company_id', 'currency_id', 'company_currency_id',
                           'id', 'move_id', 'name', 'price_subtotal')
        invoice_line_ids = self.env['account.move.line'].search_read([
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('parent_state', 'not in', ('draft', 'cancel')),
            ('move_id.invoice_user_id', '=', user_id),
            ('move_id.invoice_date', '>=', start_date),
            ('move_id.invoice_date', '<=', end_date),
            ('subscription_mrr', '=', 0), ('display_type', '=', 'product')
        ], fields=searched_fields, order='move_id')
        company_ids = self.env['res.company']
        for k, invoice_lines_it in groupby(invoice_line_ids, key=lambda x: x['move_id']):
            invoice_lines = list(invoice_lines_it)
            total_invoice = sum([d['price_subtotal'] for d in invoice_lines])
            invoice_id = self.env['account.move'].browse(invoice_lines[0]['move_id'][0])
            if invoice_lines[0]['currency_id']:
                currency_id = invoice_lines[0]['currency_id'][0]
            else:
                currency_id = invoice_lines[0]['company_currency_id'][0]
            currency_id = self.env['res.currency'].browse(currency_id)
            nrr = currency_id._convert(
                from_amount=total_invoice, date=invoice_id.date,
                to_currency=self.env.company.currency_id, company=self.env.company)
            total_nrr += nrr
            company_ids |= invoice_id.company_id
            nrr_invoice_ids.append({
                'date': invoice_id.date,
                'partner': invoice_id.partner_id.name,
                'code': invoice_id.name,
                'nrr': nrr,
                'move_id': invoice_id.id,
                'model': 'account.move',
                'company_id': invoice_id.company_id.id,
                'company_name': invoice_id.company_id.name,
            })
        return {
            'nrr': total_nrr,
            'nrr_invoices': nrr_invoice_ids,
            'company_ids': company_ids.ids,
        }

    def _get_salespersons_statistics(self, salesmen_ids, start_date, end_date):
        results = {}
        for user_id in salesmen_ids:
            results[user_id['id']] = self._get_salesperson_kpi(user_id['id'], start_date, end_date)
        return results

    @api.model
    def print_pdf(self,):
        return {
            'type': 'ir_actions_sale_subscription_dashboard_download',
            'data': {'model': "sale.order",
                     'output_format': 'pdf',
                     }
        }

    def _get_pdf(self, rendering_values):
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.get_base_url()
        body_html = self.with_context(print_mode=True)._get_body_html(rendering_values)
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
            'body_html': body_html,
        }
        body = self.env['ir.ui.view']._render_template("sale_subscription_dashboard.print_template", values=rcontext)
        # generate small footers with the date time, current company and page number.
        footer = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout",
                                                                values=dict(rcontext, subst=True,
                                                                            body=Markup(footer.decode())
                                                                            ))
        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header='', footer=footer.decode(),
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10
            }
        )

    def _get_body_html(self, rendering_values):
        company = self.env['res.company'].browse(rendering_values.get('company'))
        pdf_rendering_values = {'statistics': [],
                                'currency_symbol': company.currency_id.symbol,
                                }
        company_ids = set()
        for user_id, stats in rendering_values['salespersons_statistics'].items():
            user_id = int(user_id)
            [saleman] = (it for it in rendering_values['salesman_ids'] if it['id'] == user_id)
            stats['saleman'] = saleman
            stats['net_mrr_str'] = misc.formatLang(self.env, stats['net_new'], currency_obj=company.currency_id)
            stats['net_nrr_str'] = misc.formatLang(self.env, stats['nrr'], currency_obj=company.currency_id)
            stats['n_modifications'] = len(stats['contract_modifications'])
            stats['n_invoices'] = len(stats['nrr_invoices'])
            company_ids.update(stats['company_ids'])
            pdf_rendering_values['statistics'].append(stats)
            stats['image'] = rendering_values['graphs'][str(user_id)]

        pdf_rendering_values['n_companies'] = len(company_ids)
        body_html = self.env['ir.qweb']._render('sale_subscription_dashboard.sales_men_pdf_template', pdf_rendering_values)
        return body_html

    def _get_report_filename(self,):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        return _("Salesperson report")

    @api.model
    def _get_export_mime_type(self, file_type):
        """ Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        type_mapping = {
            'pdf': 'application/pdf',
        }
        return type_mapping.get(file_type, False)
