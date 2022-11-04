# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _lt
from odoo.osv import expression


class Project(models.Model):
    _inherit = 'project.project'

    subscriptions_count = fields.Integer('# Subscriptions', compute='_compute_subscriptions_count', groups='sales_team.group_sale_salesman')

    @api.depends('analytic_account_id')
    def _compute_subscriptions_count(self):
        if not self.analytic_account_id:
            self.subscriptions_count = 0
            return
        subscriptions_data = self.env['sale.order']._read_group([
            ('analytic_account_id', 'in', self.analytic_account_id.ids),
            ('is_subscription', '=', True),
        ], ['analytic_account_id'], ['analytic_account_id'])
        mapped_data = {data['analytic_account_id'][0]: data['analytic_account_id_count'] for data in subscriptions_data}
        for project in self:
            project.subscriptions_count = mapped_data.get(project.analytic_account_id.id, 0)

    # -------------------------------------------
    # Actions
    # -------------------------------------------

    def _get_subscription_action(self, domain=None, subscription_ids=None):
        if not domain and not subscription_ids:
            return {}
        action = self.env["ir.actions.actions"]._for_xml_id("sale_subscription.sale_subscription_action")
        action_context = {'default_analytic_account_id': self.analytic_account_id.id}
        if self.commercial_partner_id:
            action_context['default_partner_id'] = self.commercial_partner_id.id
        action.update({
            'views': [[False, 'tree'], [False, 'kanban'], [False, 'form'], [False, 'pivot'], [False, 'graph'], [False, 'cohort']],
            'context': action_context,
            'domain': domain or [('id', 'in', subscription_ids)]
        })
        if subscription_ids and len(subscription_ids) == 1:
            action["views"] = [[False, 'form']]
            action["res_id"] = subscription_ids[0]
        return action

    def action_open_project_subscriptions(self):
        self.ensure_one()
        if not self.analytic_account_id:
            return {}
        subscription_ids = self.env['sale.order']._search([('is_subscription', '=', True), ('analytic_account_id', 'in', self.analytic_account_id.ids)])
        return self._get_subscription_action(subscription_ids=list(subscription_ids))

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name == 'subscriptions':
            return self._get_subscription_action(domain, [res_id] if res_id else [])
        return super().action_profitability_items(section_name, domain, res_id)

    # -------------------------------------------
    # Project Update
    # -------------------------------------------

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['subscriptions'] = _lt('Subscriptions')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['subscriptions'] = 8
        return sequence_per_invoice_type

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            ['|', ('move_line_id', '=', False), ('move_line_id.subscription_id', '=', False)],
        ])

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        if not self.analytic_account_id:
            return profitability_items
        subscription_read_group = self.env['sale.order'].sudo()._read_group(
            [('analytic_account_id', 'in', self.analytic_account_id.ids),
             ('stage_category', '!=', 'draft'),
             ('is_subscription', '=', True),
            ],
            ['stage_category', 'sale_order_template_id', 'recurring_monthly', 'ids:array_agg(id)'],
            ['sale_order_template_id', 'stage_category'],
            lazy=False,
        )
        if not subscription_read_group:
            return profitability_items
        all_subscription_ids = []
        subscription_data_per_template_id = {}
        amount_to_invoice = 0.0
        for res in subscription_read_group:
            all_subscription_ids.extend(res['ids'])
            if res['stage_category'] != 'progress':  # then the subscriptions are closed and so nothing is to invoice.
                continue
            if not res['sale_order_template_id']:  # then we will take the recurring monthly amount that we will invoice in the next invoice(s).
                amount_to_invoice += res['recurring_monthly']
                continue
            subscription_data_per_template_id[res['sale_order_template_id'][0]] = res['recurring_monthly']

        subscription_template_dict = {}
        if subscription_data_per_template_id:
            subscription_template_dict = {
                res['id']: res['recurring_rule_count']
                for res in self.env['sale.order.template'].sudo().search_read(
                    [('id', 'in', list(subscription_data_per_template_id.keys())), ('recurring_rule_boundary', '=', 'limited')],
                    ['id', 'recurring_rule_count'],
                )
            }
        for subcription_template_id, recurring_monthly in subscription_data_per_template_id.items():
            nb_period = subscription_template_dict.get(subcription_template_id, 1)
            amount_to_invoice += recurring_monthly * nb_period

        aal_read_group = self.env['account.analytic.line'].sudo()._read_group(
            [('move_line_id.subscription_id', 'in', all_subscription_ids), ('account_id', 'in', self.analytic_account_id.ids)],
            ['amount'],
            [],
        )
        amount_invoiced = aal_read_group[0]['amount'] if aal_read_group and aal_read_group[0]['__count'] else 0.0
        revenues = profitability_items['revenues']
        section_id = 'subscriptions'
        subscription_revenue = {
            'id': section_id,
            'sequence': self._get_profitability_sequence_per_invoice_type()[section_id],
            'invoiced': amount_invoiced,
            'to_invoice': amount_to_invoice,
        }
        if with_action and all_subscription_ids and self.user_has_groups('sales_team.group_sale_salesman'):
            args = [section_id, [('id', 'in', all_subscription_ids)]]
            if len(all_subscription_ids) == 1:
                args.append(all_subscription_ids[0])
            action = {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}
            subscription_revenue['action'] = action
        revenues['data'].append(subscription_revenue)
        revenues['total']['invoiced'] += amount_invoiced
        revenues['total']['to_invoice'] += amount_to_invoice
        return profitability_items
