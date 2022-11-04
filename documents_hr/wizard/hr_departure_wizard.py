# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def _get_default_send_hr_documents_access_link(self):
        employee = self.env['hr.employee'].browse(self.env.context.get('active_id'))
        return self.env.company.documents_hr_settings and self.env.company.documents_hr_folder and employee.address_home_id.email

    send_hr_documents_access_link = fields.Boolean(
        string="Send Access Link",
        default=_get_default_send_hr_documents_access_link,
        help="Send an email to the user with a share link to all the documents he owns.")

    def action_register_departure(self):
        super().action_register_departure()
        if self.send_hr_documents_access_link:
            self.employee_id.action_send_documents_share_link()
