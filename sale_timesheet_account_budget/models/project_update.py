# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import format_amount

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        vals = super(ProjectUpdate, self)._get_template_values(project)
        if project.analytic_account_id and self.user_has_groups('account.group_account_readonly'):
            profitability = vals['profitability']
            vals['budget'] = {
                'percentage': round((-profitability.get('costs', 0) / project.budget) * 100 if project.budget != 0 else 0, 0),
                'amount': format_amount(self.env, project.budget, project.currency_id)
            }
        return vals
