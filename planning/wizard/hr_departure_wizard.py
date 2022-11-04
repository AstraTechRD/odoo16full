# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        super().action_register_departure()

        departure_date = datetime.combine(self.departure_date, time.max)
        planning_slots = self.env['planning.slot'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('end_datetime', '>=', departure_date),
        ])
        self.env['hr.employee']._manage_archived_employee_shifts(planning_slots, departure_date)
