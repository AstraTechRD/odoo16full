# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class MergeTimesheets(models.TransientModel):
    _inherit = 'hr_timesheet.merge.wizard'

    def action_merge(self):
        if any(timesheet.holiday_id for timesheet in self.timesheet_ids):
            raise UserError(_('You cannot merge timesheets that are linked to time off requests. Please use the Time Off application to modify or cancel your time off requests instead.'))

        return super().action_merge()
