# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    def _default_analytic_account_id(self):
        if self.env.context.get('project_update'):
            project = self.env['project.project'].browse(self.env.context.get('active_id'))
            return project.analytic_account_id
        return False

    analytic_account_id = fields.Many2one(default=_default_analytic_account_id)
