# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import fields, models, _
from odoo.osv import expression

class Project(models.Model):
    _inherit = "project.project"

    total_planned_amount = fields.Monetary(related='analytic_account_id.total_planned_amount')

    def action_view_budget_lines(self, domain=None):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "crossovered.budget.lines",
            "domain": expression.AND([
                [('analytic_account_id', '=', self.analytic_account_id.id)],
                domain or [],
            ]),
            'context': {'create': False, 'edit': False},
            "name": _("Budget Items"),
            'view_mode': 'tree,form',
            'views': [
                [self.env.ref('project_account_budget.crossovered_budget_lines_view_tree_inherit').id, 'tree'],
                [False, 'form']
            ]
        }

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def get_panel_data(self):
        panel_data = super().get_panel_data()
        panel_data['analytic_account_id'] = self.analytic_account_id.id
        panel_data['budget_items'] = self._get_budget_items()
        return panel_data

    def get_budget_items(self):
        self.ensure_one()
        if self.analytic_account_id and self.user_has_groups('project.group_project_user'):
            return self._get_budget_items(True)
        return {}

    def _get_budget_items(self, with_action=True):
        self.ensure_one()
        if not self.analytic_account_id:
            return {}
        budget_line_read_group = self.env['crossovered.budget.lines'].sudo()._read_group(
            [('analytic_account_id', '=', self.analytic_account_id.id), ('crossovered_budget_id', '!=', False), ('crossovered_budget_id.state', 'not in', ['draft', 'cancel'])],
            ['general_budget_id', 'planned_amount', 'practical_amount', 'ids:array_agg(id)'],
            ['general_budget_id'],
        )
        budget_data = []
        total_allocated = total_spent = 0.0
        can_see_budget_items = with_action and self.user_has_groups('account.group_account_readonly,analytic.group_analytic_accounting')
        for res in budget_line_read_group:
            name = res['general_budget_id'] and res['general_budget_id'][1]
            allocated = res['planned_amount']
            spent = res['practical_amount']
            total_allocated += allocated
            total_spent += spent
            budget_item = {'name': name, 'allocated': allocated, 'spent': spent}
            if res['ids'] and can_see_budget_items:
                budget_item['action'] = {'name': 'action_view_budget_lines', 'type': 'object', 'args': [json.dumps([('id', 'in', res['ids'])])]}
            budget_data.append(budget_item)
        can_add_budget = with_action and self.user_has_groups('account.group_account_user')
        budget_items = {
            'data': budget_data,
            'total': {'allocated': total_allocated, 'spent': total_spent},
            'can_add_budget': can_add_budget,
        }
        if can_add_budget:
            budget_items['form_view_id'] = self.env.ref('project_account_budget.crossovered_budget_view_form_dialog').id
        return budget_items
