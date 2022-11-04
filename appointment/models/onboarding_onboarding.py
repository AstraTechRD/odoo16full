# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    # Appointment Onboarding
    @api.model
    def action_close_appointment_onboarding(self):
        onboarding = self.env.ref('appointment.appointment_onboarding_panel', raise_if_not_found=False)
        if onboarding:
            onboarding.action_close()
