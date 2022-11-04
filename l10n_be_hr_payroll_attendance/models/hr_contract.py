# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _preprocess_work_hours_data_split_half(self, work_data, date_from, date_to):
        """
        Takes care of removing the extra hours from the work_data aswell as
         adding the necessary data for extra hours lines.
        """
        attendance_contracts = self.filtered(lambda c: c.work_entry_source == 'attendance' and c.wage_type == 'hourly')
        default_work_entry_type = self.structure_type_id.default_work_entry_type_id
        if not attendance_contracts or len(default_work_entry_type) != 1:
            return
        overtime_work_entry_type = self.env.ref('hr_payroll_work_entry_attendance.overtime_work_entry_type', False)
        if not overtime_work_entry_type:
            return
        overtimes = self.env['hr.attendance.overtime'].sudo().search(
            [('employee_id', 'in', self.employee_id.ids), ('duration', '>', 0),
                ('date', '>=', date_from), ('date', '<=', date_to)],
            order='date asc',
        )
        if not overtimes:
            return
        # both overtimes and work_data are sorted by date
        data_iterator = iter(work_data)
        current_data = next(data_iterator)
        for overtime in overtimes:
            while current_data and datetime.strptime(current_data['date_start:day'], '%d %b %Y') != overtime.date and\
                current_data['work_entry_type_id'][0] != default_work_entry_type.id:
                current_data = next(data_iterator)
                continue
            if not current_data:
                break
            # Remove the duration of the overtime from the data
            current_data['hours'] -= overtime.duration
        work_data.append({
            'hours': sum(overtime.duration),
            'work_entry_type_id': [overtime_work_entry_type.id],
        })
