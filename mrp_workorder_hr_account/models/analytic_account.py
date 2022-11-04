# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticAccountLine(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Account'

    employee_id = fields.Many2one('hr.employee', "Employee")
