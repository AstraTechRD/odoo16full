# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import pytz

from odoo import fields, models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals

class HrContract(models.Model):
    _inherit = 'hr.contract'

    work_entry_source = fields.Selection(
        selection_add=[('attendance', 'Attendances')],
        ondelete={'attendance': 'set default'},
    )

    def _get_more_vals_attendance_interval(self, interval):
        result = super()._get_more_vals_attendance_interval(interval)
        if interval[2]._name == 'hr.attendance':
            result.append(('attendance_id', interval[2].id))
        return result

    def _get_attendance_intervals(self, start_dt, end_dt):
        attendance_based_contracts = self.filtered(lambda c: c.work_entry_source == 'attendance')
        search_domain = [
            ('employee_id', 'in', attendance_based_contracts.employee_id.ids),
            ('check_in', '<', end_dt),
            ('check_out', '>', start_dt), #We ignore attendances which don't have a check_out
        ]
        resource_ids = attendance_based_contracts.employee_id.resource_id.ids
        attendances = self.env['hr.attendance'].sudo().search(search_domain) if attendance_based_contracts\
            else self.env['hr.attendance']
        intervals = defaultdict(list)
        for attendance in attendances:
            intervals[attendance.employee_id.resource_id.id].append((
                max(start_dt, pytz.utc.localize(attendance.check_in)),
                min(end_dt, pytz.utc.localize(attendance.check_out)),
                attendance))
        mapped_intervals = {r: WorkIntervals(intervals[r]) for r in resource_ids}
        mapped_intervals.update(super(HrContract, self - attendance_based_contracts)._get_attendance_intervals(
            start_dt, end_dt))
        return mapped_intervals
