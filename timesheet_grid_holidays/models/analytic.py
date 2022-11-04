# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line']

    def _should_not_display_timer(self):
        self.ensure_one()
        return super()._should_not_display_timer() or self.task_id.is_timeoff_task
