# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    prevent_old_timesheets_encoding = fields.Boolean(related="company_id.prevent_old_timesheets_encoding", readonly=False)
    reminder_user_allow = fields.Boolean("Employee Reminder", related='company_id.timesheet_mail_employee_allow', readonly=False)
    reminder_user_delay = fields.Integer("Days to Remind User", related='company_id.timesheet_mail_employee_delay', readonly=False,
        help="Numbers of days after the end of the week/month after which an automatic email reminder will be sent to timesheet users that still have timesheets to encode (according to their working hours).")
    reminder_user_interval = fields.Selection(string='User Reminder Frequency', required=True,
        related='company_id.timesheet_mail_employee_interval', readonly=False)

    reminder_manager_allow = fields.Boolean("Manager Reminder", related='company_id.timesheet_mail_manager_allow', readonly=False)
    reminder_manager_delay = fields.Integer("Days to Remind Manager", related='company_id.timesheet_mail_manager_delay', readonly=False,
        help="Number of days after the end of the week/month after which an automatic email reminder will be sent to timesheet managers that still have timesheets to validate.")
    reminder_manager_interval = fields.Selection(string='Manager Reminder Frequency', required=True,
        related='company_id.timesheet_mail_manager_interval', readonly=False)
    timesheet_min_duration = fields.Integer('Minimal Duration', default=15, config_parameter='timesheet_grid.timesheet_min_duration')
    timesheet_rounding = fields.Integer('Round up', default=15, config_parameter='timesheet_grid.timesheet_rounding')

    def set_values(self):
        super().set_values()
        if self.prevent_old_timesheets_encoding:
            employee_ids = self.env['hr.employee'].sudo()._search([('company_id', '=', self.company_id.id)])
            self.env['account.analytic.line']._search_last_validated_timesheet_date(list(employee_ids))
