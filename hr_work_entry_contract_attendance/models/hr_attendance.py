#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _create_work_entries(self):
        # Upon creating or closing an attendance, create the work entry directly if the attendance
        # was created within an already generated period
        # This code assumes that attendances are not created/written in big batches
        work_entries_vals_list = []
        for attendance in self:
            # Filter closed attendances
            if not attendance.check_out:
                continue
            contracts = attendance.employee_id.sudo()._get_contracts(
                attendance.check_in, attendance.check_out, states=['open', 'close'])
            for contract in contracts:
                if contract.work_entry_source != 'attendance':
                    continue
                if attendance.check_out >= contract.date_generated_from and attendance.check_in <= contract.date_generated_to:
                    work_entries_vals_list += contracts._get_work_entries_values(attendance.check_in, attendance.check_out)
        if work_entries_vals_list:
            self.env['hr.work.entry'].sudo().create(work_entries_vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_work_entries()
        return res

    def write(self, vals):
        new_check_out = vals.get('check_out')
        open_attendances = self.filtered(lambda a: not a.check_out) if new_check_out else self.env['hr.attendance']
        res = super().write(vals)
        open_attendances._create_work_entries()
        return res

    def unlink(self):
        # Archive linked work entries upon deleting attendances
        self.env['hr.work.entry'].sudo().search([('attendance_id', 'in', self.ids)]).write({'active': False})
        return super().unlink()
