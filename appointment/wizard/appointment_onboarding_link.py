# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_join

from odoo import api, fields, models


class AppointmentOnboardingLink(models.TransientModel):
    _name = 'appointment.onboarding.link'
    _description = 'Get a link to an appointment type during the onboarding'

    appointment_type_id = fields.Many2one('appointment.type', required=True, readonly=True, ondelete='cascade')
    short_code = fields.Char('Short Code', required=True)
    base_book_url = fields.Char(
        'Base Link URL', compute="_compute_base_book_url", required=True, readonly=True)

    @api.depends('short_code')
    def _compute_base_book_url(self):
        self.base_book_url = url_join(self.get_base_url(), '/book/')

    def search_or_create_onboarding_invite(self):
        """ Allows multiple accesses to a special invite using during the
        onboarding (slug of the appointment type as default shortcode).
        """
        invite = self.env['appointment.invite'].search([
            ('short_code', '=', self.short_code)
        ]) or self.env['appointment.invite'].create({
            'appointment_type_ids': self.appointment_type_id.ids,
            'short_code': self.short_code,
        })

        # Avoid multiplying RPC calls. Adequate because this function is only
        # meant to be called when pushing one of the buttons on link wizard.
        onboarding_invite_step = self.env.ref('appointment.appointment_onboarding_preview_invite_step',
                                              raise_if_not_found=False)
        if not onboarding_invite_step:
            return
        was_done = onboarding_invite_step.current_step_state in {'just_done', 'done'}
        onboarding_invite_step.action_set_just_done()
        if not was_done:
            #  make sure to check first step as well as there is now always an appointment type.
            self.env.ref(
                'appointment.appointment_onboarding_create_appointment_type_step',
                raise_if_not_found=False).action_set_just_done()

        return {
            'bookUrl': invite.book_url,
            'wasFirstValidation': not was_done,
        }
