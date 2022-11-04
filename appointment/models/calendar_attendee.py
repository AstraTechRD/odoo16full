# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Attendee(models.Model):
    _inherit = 'calendar.attendee'

    def _compute_mail_tz(self):
        toupdate = self.filtered(lambda r: r.event_id.appointment_type_id.appointment_tz)
        for attendee in toupdate:
            attendee.mail_tz = attendee.event_id.appointment_type_id.appointment_tz
        super(Attendee, self - toupdate)._compute_mail_tz()
