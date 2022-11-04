# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(compute='_compute_name', store=True, string='Description', readonly=False)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(string='Code', related='work_entry_type_id.code')
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Type', required=True, help="The code that can be used in the salary rules")
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    is_paid = fields.Boolean(compute='_compute_is_paid', store=True)
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True, copy=True)
    contract_id = fields.Many2one(related='payslip_id.contract_id', string='Contract',
        help="The contract this worked days should be applied to")
    currency_id = fields.Many2one('res.currency', related='payslip_id.currency_id')

    @api.depends(
        'work_entry_type_id', 'payslip_id', 'payslip_id.struct_id',
        'payslip_id.employee_id', 'payslip_id.contract_id', 'payslip_id.struct_id', 'payslip_id.date_from', 'payslip_id.date_to')
    def _compute_is_paid(self):
        unpaid = {struct.id: struct.unpaid_work_entry_type_ids.ids for struct in self.mapped('payslip_id.struct_id')}
        for worked_days in self:
            worked_days.is_paid = (worked_days.work_entry_type_id.id not in unpaid[worked_days.payslip_id.struct_id.id]) if worked_days.payslip_id.struct_id.id in unpaid else False

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        for worked_days in self:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state not in ['draft', 'verify']:
                continue
            if not worked_days.contract_id or worked_days.code == 'OUT':
                worked_days.amount = 0
                continue
            if worked_days.payslip_id.wage_type == "hourly":
                worked_days.amount = worked_days.payslip_id.contract_id.hourly_wage * worked_days.number_of_hours if worked_days.is_paid else 0
            else:
                worked_days.amount = worked_days.payslip_id.contract_id.contract_wage * worked_days.number_of_hours / (worked_days.payslip_id.sum_worked_hours or 1) if worked_days.is_paid else 0

    @api.depends('work_entry_type_id')
    def _compute_name(self):
        for worked_days in self:
            worked_days.name = worked_days.work_entry_type_id.name
