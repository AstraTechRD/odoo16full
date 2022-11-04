#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    is_credit_time = fields.Boolean(
        string='Credit time', readonly=True,
        help="This is a credit time work entry.")

    def _get_leaves_entries_outside_schedule(self):
        return super()._get_leaves_entries_outside_schedule().filtered(lambda w: not w.is_credit_time)

    def _get_duration_is_valid(self):
        return super()._get_duration_is_valid() and not self.is_credit_time

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')
        leaves = self.env['hr.leave']
        for work_entry in res:
            if work_entry.work_entry_type_id == partial_sick_work_entry_type and work_entry.leave_id:
                leaves |= work_entry.leave_id
        for leave in leaves.sudo():
            leave.activity_schedule(
                'mail.mail_activity_data_todo',
                note=_("Sick time off to report to DRS for %s.", leave.date_from.strftime('%B %Y')),
                user_id=leave.holiday_status_id.responsible_id.id or self.env.user.id,
            )
        return res
