# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo.addons.appointment_hr.tests.common import AppointmentHrCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged, users


@tagged('appointment_slots')
class AppointmentHrTest(AppointmentHrCommon):

    @classmethod
    def setUpClass(cls):
        super(AppointmentHrTest, cls).setUpClass()
        cls.apt_type_bxls_2days.write({
            'work_hours_activated': True,
        })

    @users('apt_manager')
    def test_generate_slots_recurring(self):
        """ Generates recurring slots, check begin and end slot boundaries. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 5)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_UTC(self):
        """ Generates recurring slots, check begin and end slot boundaries. Force
        UTC results event if everything is Europe/Brussels based. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 5)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_start_hours': [7, 8, 9, 10, 12],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_wleaves(self):
        """ Generates recurring slots, check begin and end slot boundaries
        with leaves involved. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # create personal leaves
        _leaves = self._create_leaves(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 2 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=2)),
             (self.reference_monday + timedelta(days=7), # next Monday: one hour
              self.reference_monday + timedelta(days=7, hours=1))
            ],
        )
        # add global leaves
        _leaves += self._create_leaves(
            self.env['res.users'],
            [(self.reference_monday + timedelta(days=8), # next Tuesday is bank holiday
              self.reference_monday + timedelta(days=8, hours=12))
            ],
            calendar=self.staff_user_bxls.resource_calendar_id,
        )

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 5)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_day_specific': {
                (self.reference_monday + timedelta(days=1)).date(): [
                    {'end': 11, 'start': 10},
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13}
                ],  # leaves on 7-9 UTC
                (self.reference_monday + timedelta(days=7)).date(): [
                    {'end': 10, 'start': 9},
                    {'end': 11, 'start': 10},
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13}
                ],  # leaves on 7-8
                (self.reference_monday + timedelta(days=8)).date(): [],  # 12 hours long bank holiday
             },
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_recurring_wmeetings(self):
        """ Generates recurring slots, check begin and end slot boundaries
        with leaves involved. """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)

        # create meetings
        _meetings = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday + timedelta(days=1),  # 3 hours first Tuesday
              self.reference_monday + timedelta(days=1, hours=3),
              False
             ),
             (self.reference_monday + timedelta(days=7), # next Monday: one full day
              self.reference_monday + timedelta(days=7, hours=1),
              True,
             ),
             (self.reference_monday + timedelta(days=8, hours=2), # 1 hour next Tuesday (9 UTC)
              self.reference_monday + timedelta(days=8, hours=3),
              False,
             ),
             (self.reference_monday + timedelta(days=8, hours=3), # 1 hour next Tuesday (10 UTC, declined)
              self.reference_monday + timedelta(days=8, hours=4),
              False,
             ),
             (self.reference_monday + timedelta(days=8, hours=5), # 2 hours next Tuesday (12 UTC)
              self.reference_monday + timedelta(days=8, hours=7),
              False,
             ),
            ]
        )
        attendee = _meetings[-2].attendee_ids.filtered(lambda att: att.partner_id == self.staff_user_bxls.partner_id)
        attendee.do_decline()

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('Europe/Brussels')

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 3, 5)  # last day of last week of February
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_day_specific': {
                (self.reference_monday + timedelta(days=1)).date(): [
                    {'end': 12, 'start': 11},
                    {'end': 14, 'start': 13},
                ],  # meetings on 7-10 UTC
                (self.reference_monday + timedelta(days=7)).date(): [],  # on meeting "allday"
                (self.reference_monday + timedelta(days=8)).date(): [
                    {'end': 9, 'start': 8},
                    {'end': 10, 'start': 9},
                    {'end': 12, 'start': 11},
                ],  # meetings 9-10 and 12-14
             },
             'slots_start_hours': [8, 9, 10, 11, 13],  # based on appointment type start hours of slots but 12 is pause midi
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )
