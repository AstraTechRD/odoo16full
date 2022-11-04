# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import models


class Partner(models.Model):
    _inherit = "res.partner"

    def calendar_verify_availability(self, date_start, date_end):
        """ Verify availability of the partner(s) between 2 datetimes on their calendar.

        :param datetime date_start: beginning of slot boundary. Not timezoned UTC;
        :param datetime date_end: end of slot boundary. Not timezoned UTC;
        """
        all_events = self.env['calendar.event'].search(
            ['&',
             ('partner_ids', 'in', self.ids),
             '&',
             ('stop', '>', datetime.combine(date_start, time.min)),
             ('start', '<', datetime.combine(date_end, time.max)),
            ],
            order='start asc',
        )
        for event in all_events:
            if event.allday or (event.start < date_end and event.stop > date_start):
                if event.attendee_ids.filtered_domain(
                        [('state', '!=', 'declined'),
                         ('partner_id', 'in', self.ids)]
                    ):
                    return False

        return True
