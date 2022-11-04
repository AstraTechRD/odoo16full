# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipInputType(models.Model):
    _name = 'hr.payslip.input.type'
    _description = 'Payslip Input Type'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    struct_ids = fields.Many2many('hr.payroll.structure', string='Availability in Structure', help='This input will be only available in those structure. If empty, it will be available in all payslip.')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
