# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.appointment.controllers.calendar_view import AppointmentCalendarView
from odoo.exceptions import AccessError
from odoo.http import request, route


class AppointmentHRCalendarView(AppointmentCalendarView):

    # Utility Methods
    # ----------------------------------------------------------

    def _prepare_appointment_type_anytime_values(self):
        appt_type_vals = super()._prepare_appointment_type_anytime_values()
        appt_type_vals.update(work_hours_activated=True)
        return appt_type_vals
