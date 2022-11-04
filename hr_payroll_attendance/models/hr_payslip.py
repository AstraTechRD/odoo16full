#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from datetime import datetime

from odoo import api, fields, models
from odoo.osv import expression

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_count = fields.Integer(compute='_compute_attendance_count', groups="hr_attendance.group_hr_attendance_user")

    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_attendance_count(self):
        self.attendance_count = 0
        attendance_based_slips = self.filtered(lambda p: p.contract_id.work_entry_source == 'attendance')
        if not attendance_based_slips:
            return
        domain = []
        slip_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        for slip in attendance_based_slips:
            slip_by_employee[slip.employee_id.id] |= slip
            domain = expression.OR([
                domain,
                [
                    ('employee_id', '=', slip.employee_id.id),
                    ('check_in', '<=', slip.date_to),
                    ('check_out', '>=', slip.date_from),
                ]
            ])
        read_group = self.env['hr.attendance']._read_group(domain, fields=['id'], groupby=['employee_id', 'check_in:day'], lazy=False)
        for result in read_group:
            slips = slip_by_employee[result['employee_id'][0]]
            date = datetime.strptime(result['check_in:day'], '%d %b %Y').date()
            for slip in slips:
                if slip.date_from <= date and date <= slip.date_to:
                    slip.attendance_count += result['__count']

    def action_open_attendances(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('hr_attendance.hr_attendance_action_employee')
        action['context'] = {
            'create': False,
            'search_default_employee_id': self.employee_id.id,
        }
        action['domain'] = [('check_in', '<=', self.date_to), ('check_out', '>=', self.date_from)]
        return action
