# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger


@tagged('appointment_slots')
class AppointmentTest(AppointmentCommon):

    @users('apt_manager')
    def test_appointment_type_create(self):
        # Custom: current user set as default, otherwise accepts only 1 user
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom without user',
        })
        self.assertEqual(apt_type.staff_user_ids, self.apt_manager)

        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'staff_user_ids': [(4, self.staff_users[0].id)],
            'name': 'Custom with user',
        })
        self.assertEqual(apt_type.staff_user_ids, self.staff_users[0])

        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({
                'category': 'custom',
                'staff_user_ids': self.staff_users.ids,
                'name': 'Custom with users',
            })

    @users('apt_manager')
    def test_appointment_type_create_anytime(self):
        # Any Time: only 1 / employee
        apt_type = self.env['appointment.type'].create({
            'category': 'anytime',
            'name': 'Any time on me',
        })
        self.assertEqual(apt_type.staff_user_ids, self.apt_manager)

        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({
                'category': 'anytime',
                'name': 'Any time on me, duplicate',
            })

        with self.assertRaises(ValidationError):
            self.env['appointment.type'].create({
                'name': 'Any time without employee',
                'category': 'anytime',
                'staff_user_ids': [self.staff_users.ids]
            })

    @mute_logger('odoo.sql_db')
    @users('apt_manager')
    def test_appointment_slot_start_end_hour_auto_correction(self):
        """ Test the autocorrection of invalid intervals [start_hour, end_hour]. """
        appt_type = self.env['appointment.type'].create({
            'category': 'website',
            'name': 'Schedule a demo',
            'appointment_duration': 1,
            'slot_ids': [(0, 0, {
                'weekday': '1',  # Monday
                'start_hour': 9,
                'end_hour': 17,
            })],
        })
        appt_form = Form(appt_type)

        # invalid interval, no adaptation because start_hour is not changed
        with self.assertRaises(ValidationError):
            with appt_form.slot_ids.edit(0) as slot_form:
                slot_form.end_hour = 8
            appt_form.save()

        # invalid interval, adapted because start_hour is changed
        with appt_form.slot_ids.edit(0) as slot_form:
            slot_form.start_hour = 18
            self.assertEqual(slot_form.start_hour, 18)
            self.assertEqual(slot_form.end_hour, 19)
        appt_form.save()

        # empty interval, adapted because start_hour is changed
        with appt_form.slot_ids.edit(0) as slot_form:
            slot_form.start_hour = 19
            self.assertEqual(slot_form.start_hour, 19)
            self.assertEqual(slot_form.end_hour, 20)
        appt_form.save()

        # invalid interval, end_hour not adapted [23.5, 19] because it will exceed 24
        with self.assertRaises(ValidationError):
            with appt_form.slot_ids.edit(0) as slot_form:
                slot_form.start_hour = 23.5
            appt_form.save()

    def test_generate_slots_until_midnight(self):
        """ Generate recurring slots until midnight. """
        appt_type = self.env['appointment.type'].create({
            'category': 'website',
            'name': 'Schedule a demo',
            'max_schedule_days': 1,
            'appointment_duration': 1,
            'appointment_tz': 'Europe/Brussels',
            'slot_ids': [(0, 0, {
                'weekday': '1',  # Monday
                'start_hour': 18,
                'end_hour': 0,
            })],
            'staff_user_ids': [(4, self.staff_user_bxls.id)],
        }).with_user(self.env.user)

        with freeze_time(self.reference_now):
            slots = appt_type._get_appointment_slots('Europe/Brussels')

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
             'slots_start_hours': [18, 19, 20, 21, 22, 23],
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_enddate': self.reference_monday.date(),  # only test that day
             }
        )


    @users('apt_manager')
    def test_appointment_type_custom_badge(self):
        """ Check that the number of previous and next slots in the badge are correctly based on availability """
        reference_start = self.reference_monday.replace(microsecond=0)
        unique_slots = [{
            'allday': True,
            'end_datetime': reference_start + timedelta(days=delta_day + 1),
            'slot_type': 'unique',
            'start_datetime': reference_start + timedelta(days=delta_day),
        } for delta_day in (0, 1, 31, 62, 63)]
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom Appointment Type',
            'slot_ids': [(5, 0)] + [(0, 0, slot) for slot in unique_slots],
        })

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        nb_february_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_users=self.apt_manager))
        nb_march_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(3, 2022)],
            filter_users=self.apt_manager))
        nb_april_slots = len(self._filter_appointment_slots(
            slots, filter_months=[(4, 2022)],
            filter_users=self.apt_manager))

        # February month
        self.assertEqual(slots[0]['nb_slots_previous_months'], 0)
        self.assertEqual(slots[0]['nb_slots_next_months'], nb_march_slots + nb_april_slots)

        # March month
        self.assertEqual(slots[1]['nb_slots_previous_months'], nb_february_slots)
        self.assertEqual(slots[1]['nb_slots_next_months'], nb_april_slots)

        # April month
        self.assertEqual(slots[2]['nb_slots_previous_months'], nb_february_slots + nb_march_slots)
        self.assertEqual(slots[2]['nb_slots_next_months'], 0)

        # Create a meeting during the duration of the first slot
        self._create_meetings(self.apt_manager, [(
            reference_start + timedelta(hours=2),
            reference_start + timedelta(hours=3),
            False,
        )])

        previous_nb_feb_slots = nb_february_slots

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')

        nb_february_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_users=self.apt_manager))
        nb_march_slots = len(self._filter_appointment_slots(
            slots,
            filter_months=[(3, 2022)],
            filter_users=self.apt_manager))
        nb_april_slots = len(self._filter_appointment_slots(
            slots, filter_months=[(4, 2022)],
            filter_users=self.apt_manager))

        # February month
        self.assertEqual(slots[0]['nb_slots_previous_months'], 0)
        self.assertEqual(slots[0]['nb_slots_next_months'], nb_march_slots + nb_april_slots)
        self.assertEqual(nb_february_slots, previous_nb_feb_slots - 1)

        # March month
        self.assertEqual(slots[1]['nb_slots_previous_months'], nb_february_slots)
        self.assertEqual(slots[1]['nb_slots_next_months'], nb_april_slots)

        # April month
        self.assertEqual(slots[2]['nb_slots_previous_months'], nb_february_slots + nb_march_slots)
        self.assertEqual(slots[2]['nb_slots_next_months'], 0)

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
             'slots_start_hours': [8, 9, 10, 11, 12, 13],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
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
             'slots_start_hours': [7, 8, 9, 10, 11, 12],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('admin')
    def test_generate_slots_recurring_westrict(self):
        """ Generates recurring slots, check user restrictions """
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user)
        # add second staff user and split days based on the two people
        apt_type.write({'staff_user_ids': [(4, self.staff_user_aust.id)]})
        apt_type.slot_ids.filtered(lambda slot: slot.weekday == '1').write({
            'restrict_to_user_ids': [(4, self.staff_user_bxls.id)],
        })
        apt_type.slot_ids.filtered(lambda slot: slot.weekday != '1').write({
            'restrict_to_user_ids': [(4, self.staff_user_aust.id)],
        })

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
             'slots_start_hours': [8, 9, 10, 11, 12, 13],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

        # check staff_user_id
        monday_slots = [
            slot
            for month in slots for week in month['weeks'] for day in week
            for slot in day['slots']
            if day['day'].weekday() == 0
        ]
        tuesday_slots = [
            slot
            for month in slots for week in month['weeks'] for day in week
            for slot in day['slots']
            if day['day'].weekday() == 1
        ]
        self.assertEqual(len(monday_slots), 18, 'Slots: 3 mondays of 6 slots')
        self.assertTrue(all(slot['staff_user_id'] == self.staff_user_bxls.id for slot in monday_slots))
        self.assertEqual(len(tuesday_slots), 12, 'Slots: 2 tuesdays of 6 slots (3rd tuesday is out of range')
        self.assertTrue(all(slot['staff_user_id'] == self.staff_user_aust.id for slot in tuesday_slots))

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
                    {'end': 13, 'start': 12},
                    {'end': 14, 'start': 13},
                ],  # meetings on 7-10 UTC
                (self.reference_monday + timedelta(days=7)).date(): [],  # on meeting "allday"
                (self.reference_monday + timedelta(days=8)).date(): [
                    {'end': 9, 'start': 8},
                    {'end': 10, 'start': 9},
                    {'end': 12, 'start': 11},
                    {'end': 13, 'start': 12},
                ],  # meetings 9-10 and 12-14
             },
             'slots_start_hours': [8, 9, 10, 11, 12, 13],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_generate_slots_unique(self):
        """ Check unique slots (note: custom appointment type does not check working
        hours). """
        unique_slots = [{
            'start_datetime': self.reference_monday.replace(microsecond=0),
            'end_datetime': (self.reference_monday + timedelta(hours=1)).replace(microsecond=0),
            'allday': False,
        }, {
            'start_datetime': (self.reference_monday + timedelta(days=1)).replace(microsecond=0),
            'end_datetime': (self.reference_monday + timedelta(days=2)).replace(microsecond=0),
            'allday': True,
        }]
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom with unique slots',
            'slot_ids': [(5, 0)] + [
                (0, 0, {'allday': slot['allday'],
                        'end_datetime': slot['end_datetime'],
                        'slot_type': 'unique',
                        'start_datetime': slot['start_datetime'],
                       }
                ) for slot in unique_slots
            ],
        })
        self.assertEqual(apt_type.category, 'custom', "It should be a custom appointment type")
        self.assertEqual(apt_type.staff_user_ids, self.apt_manager)
        self.assertEqual(len(apt_type.slot_ids), 2, "Two slots should have been assigned to the appointment type")

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
                self.reference_monday.date(): [{'end': 9, 'start': 8}],  # first unique 1 hour long
                (self.reference_monday + timedelta(days=1)).date(): [{'allday': True, 'end': False, 'start': 8}],  # second unique all day-based
             },
             'slots_start_hours': [],  # all slots in this tests are unique, other dates have no slots
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_multi_user_slot_availabilities(self):
        """ Check that when called with no user / one user / several users, the methods computing the slots work as expected:
        if no user is set, all users of the appointment_type will be used. If one or more users are set, they will be used to
        compute availabilities. If users given as argument is not among the staff of the appointment type, return empty list.
        This test only concern random appointments: if it were 'chosen' assignment, then the dropdown of user selection would
        be in the view. Hence, in practice, only one user would be used to generate / update the slots : the one selected. For
        random ones, the users can be multiple if a filter is set, assigning randomly among several users. This tests asserts
        that _get_appointment_slots returns slots properly when called with several users too. If no filter, then the update
        method would be called with staff_users = False (since select not in view, getting the input value returns false) """
        reference_monday = self.reference_monday.replace(microsecond=0)
        reccuring_slots_utc = [{
            'weekday': '1',
            'start_hour': 6.0,  # 1 slot : Monday 06:00 -> 07:00
            'end_hour': 7.0,
        }, {
            'weekday': '2',
            'start_hour': 9.0,  # 2 slots : Tuesday 09:00 -> 11:00
            'end_hour': 11.0,
        }]
        apt_type_UTC = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'assign_method': 'random',
            'category': 'website',
            'max_schedule_days': 5,  # Only consider the first three slots
            'name': 'Private Guitar Lesson',
            'slot_ids': [(0, False, {
                'weekday': slot['weekday'],
                'start_hour': slot['start_hour'],
                'end_hour': slot['end_hour'],
            }) for slot in reccuring_slots_utc],
            'staff_user_ids': [self.staff_user_aust.id, self.staff_user_bxls.id],
        })

        exterior_staff_user = self.apt_manager
        # staff_user_bxls is only available on Wed and staff_user_aust only on Mon and Tue
        self._create_meetings(
            self.staff_user_bxls,
            [(reference_monday - timedelta(hours=1),  # Monday 06:00 -> 07:00
              reference_monday,
              False
              )]
        )
        self._create_meetings(
            self.staff_user_aust,
            [(reference_monday + timedelta(days=1, hours=2),  # Tuesday 09:00 -> 11:00
              reference_monday + timedelta(days=1, hours=4),
              False
              )]
        )

        with freeze_time(self.reference_now):
            slots_no_user = apt_type_UTC._get_appointment_slots('UTC')
            slots_exterior_user = apt_type_UTC._get_appointment_slots('UTC', exterior_staff_user)
            slots_user_aust = apt_type_UTC._get_appointment_slots('UTC', self.staff_user_aust)
            slots_user_all = apt_type_UTC._get_appointment_slots('UTC', self.staff_user_bxls | self.staff_user_aust)
            slots_user_bxls_exterior_user = apt_type_UTC._get_appointment_slots('UTC', self.staff_user_bxls | exterior_staff_user)

        self.assertTrue(len(self._filter_appointment_slots(slots_no_user)) == 3)
        self.assertFalse(slots_exterior_user)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_aust)) == 1)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_all)) == 3)
        self.assertTrue(len(self._filter_appointment_slots(slots_user_bxls_exterior_user)) == 2)

    @users('apt_manager')
    def test_slots_for_today(self):
        test_reference_now = datetime(2022, 2, 14, 11, 0, 0)  # is a Monday
        appointment = self.env['appointment.type'].create({
            'appointment_tz': 'UTC',
            'min_schedule_hours': 1.0,
            'max_schedule_days': 8,
            'name': 'Test',
            'slot_ids': [(0, 0, {
                'weekday': str(test_reference_now.isoweekday()),
                'start_hour': 6,
                'end_hour': 18,
            })],
            'staff_user_ids': [self.staff_user_bxls.id],
        })
        first_day = (test_reference_now + timedelta(hours=appointment.min_schedule_hours)).astimezone(pytz.UTC)
        last_day = (test_reference_now + timedelta(days=appointment.max_schedule_days)).astimezone(pytz.UTC)
        with freeze_time(test_reference_now):
            slots = appointment._slots_generate(first_day, last_day, 'UTC')

        self.assertEqual(len(slots), 18, '2 mondays of 12 slots but 6 would be before reference date')
        for slot in slots:
            self.assertTrue(
                test_reference_now.astimezone(pytz.UTC) < slot['UTC'][0].astimezone(pytz.UTC),
                "A slot shouldn't be generated before the first_day datetime")

    @users('staff_user_aust')
    def test_timezone_delta(self):
        """ Test timezone delta. Not sure what original test was really doing. """
        # As if the second user called the function
        apt_type = self.apt_type_bxls_2days.with_user(self.env.user).with_context(
            lang='en_US',
            tz=self.staff_user_aust.tz,
            uid=self.staff_user_aust.id,
        )

        # Do what the controller actually does, aka sudo
        with freeze_time(self.reference_now):
            slots = apt_type.sudo()._get_appointment_slots('Australia/West', filter_users=None)

        global_slots_startdate = self.reference_now_monthweekstart
        global_slots_enddate = date(2022, 4, 2)  # last day of last week of March
        self.assertSlots(
            slots,
            [{'name_formated': 'February 2022',
              'month_date': datetime(2022, 2, 1),
              'weeks_count': 5,  # 31/01 -> 28/02 (06/03)
             },
             {'name_formated': 'March 2022',
              'month_date': datetime(2022, 3, 1),
              'weeks_count': 5,  # 28/02 -> 28/03 (03/04)
             }
            ],
            {'enddate': global_slots_enddate,
             'startdate': global_slots_startdate,
             'slots_enddate': self.reference_now.date() + timedelta(days=15),  # maximum 2 weeks of slots
             'slots_start_hours': [15, 16, 17, 18, 19, 20],  # based on appointment type start hours of slots, no work hours / no meetings / no leaves, set in UTC+8
             'slots_startdate': self.reference_monday.date(),  # first Monday after reference_now
             'slots_weekdays_nowork': range(2, 7)  # working hours only on Monday/Tuesday (0, 1)
            }
        )

    @users('apt_manager')
    def test_unique_slots_availabilities(self):
        """ Check that the availability of each unique slot is correct.
        First we test that the 2 unique slots of the custom appointment type
        are available. Then we check that there is now only 1 availability left
        after the creation of a meeting which encompasses a slot. """
        reference_monday = self.reference_monday.replace(microsecond=0)
        unique_slots = [{
            'allday': False,
            'end_datetime': reference_monday + timedelta(hours=1),
            'start_datetime': reference_monday,
        }, {
            'allday': False,
            'end_datetime': reference_monday + timedelta(hours=3),
            'start_datetime': reference_monday + timedelta(hours=2),
        }]
        apt_type = self.env['appointment.type'].create({
            'category': 'custom',
            'name': 'Custom with unique slots',
            'slot_ids': [(0, 0, {
                'allday': slot['allday'],
                'end_datetime': slot['end_datetime'],
                'slot_type': 'unique',
                'start_datetime': slot['start_datetime'],
                }) for slot in unique_slots
            ],
        })

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')
        # get all monday slots where apt_manager is available
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_weekdays=[0],
            filter_users=self.apt_manager)
        self.assertEqual(len(available_unique_slots), 2)

        # Create a meeting encompassing the first unique slot
        self._create_meetings(self.apt_manager, [(
            unique_slots[0]['start_datetime'],
            unique_slots[0]['end_datetime'],
            False,
        )])

        with freeze_time(self.reference_now):
            slots = apt_type._get_appointment_slots('UTC')
        available_unique_slots = self._filter_appointment_slots(
            slots,
            filter_months=[(2, 2022)],
            filter_weekdays=[0],
            filter_users=self.apt_manager)
        self.assertEqual(len(available_unique_slots), 1)
        self.assertEqual(
            available_unique_slots[0]['datetime'],
            unique_slots[1]['start_datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        )
