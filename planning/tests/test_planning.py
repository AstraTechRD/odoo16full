# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import Form

from .common import TestCommonPlanning

class TestPlanning(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.datetime.now)
        with freeze_time('2019-5-1'):
            cls.setUpEmployees()
        calendar_joseph = cls.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 13, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 14, 'hour_to': 18, 'day_period': 'afternoon'}),
            ]
        })
        calendar_bert = cls.env['resource.calendar'].create({
            'name': 'Calendar 2',
            'tz': 'UTC',
            'hours_per_day': 4,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'morning'}),
            ],
        })
        calendar = cls.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })
        cls.env.user.company_id.resource_calendar_id = calendar
        cls.employee_joseph.resource_calendar_id = calendar_joseph
        cls.employee_bert.resource_calendar_id = calendar_bert
        cls.slot = cls.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 27, 18, 0, 0),
        })
        cls.template = cls.env['planning.slot.template'].create({
            'start_time': 11,
            'duration': 4,
        })

    def test_allocated_hours_defaults(self):
        self.assertEqual(self.slot.allocated_hours, 8, "It should follow the calendar of the resource to compute the allocated hours.")
        self.assertEqual(self.slot.allocated_percentage, 100, "It should have the default value")

    def test_change_percentage(self):
        self.slot.allocated_percentage = 60
        self.assertEqual(self.slot.allocated_hours, 8 * 0.60, "It should 60%% of working hours")

    def test_change_hours_more(self):
        self.slot.allocated_hours = 12
        self.assertEqual(self.slot.allocated_percentage, 150)

    def test_change_hours_less(self):
        self.slot.allocated_hours = 4
        self.assertEqual(self.slot.allocated_percentage, 50)

    def test_change_start(self):
        self.slot.start_datetime += relativedelta(hours=2)
        self.assertEqual(self.slot.allocated_percentage, 100, "It should still be 100%")
        self.assertEqual(self.slot.allocated_hours, 8, "It should decreased by 2 hours")

    def test_change_start_partial(self):
        self.slot.allocated_percentage = 80
        self.slot.start_datetime += relativedelta(hours=2)
        self.slot.flush_recordset()
        self.slot.invalidate_recordset()
        self.assertEqual(self.slot.allocated_hours, 8 * 0.8, "It should be decreased by 2 hours and percentage applied")
        self.assertEqual(self.slot.allocated_percentage, 80, "It should still be 80%")

    def test_change_end(self):
        self.slot.end_datetime -= relativedelta(hours=2)
        self.assertEqual(self.slot.allocated_percentage, 100, "It should still be 100%")
        self.assertEqual(self.slot.allocated_hours, 8, "It should decreased by 2 hours")

    def test_set_template(self):
        self.env.user.tz = 'Europe/Brussels'
        self.slot.template_id = self.template
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 9, 0), 'It should set time from template, in user timezone (11am CET -> 9am UTC)')

    def test_change_employee_with_template(self):
        self.slot.template_id = self.template
        self.env.flush_all()

        # simulate public user (no tz)
        self.env.user.tz = False
        self.slot.resource_id = self.employee_janice.resource_id
        self.assertEqual(self.slot.template_id, self.template, 'It should keep the template')
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should adjust for employee timezone: 11am EDT -> 3pm UTC')

    def test_change_employee(self):
        """ Ensures that changing the employee does not have an impact to the shift. """
        self.env.user.tz = 'UTC'
        self.slot.resource_id = self.employee_joseph.resource_id
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 8, 0), 'It should not adjust to employee calendar')
        self.assertEqual(self.slot.end_datetime, datetime(2019, 6, 27, 18, 0), 'It should not adjust to employee calendar')
        self.slot.resource_id = self.employee_bert.resource_id
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 8, 0), 'It should not adjust to employee calendar')
        self.assertEqual(self.slot.end_datetime, datetime(2019, 6, 27, 18, 0), 'It should not adjust to employee calendar')

    def test_create_with_employee(self):
        """ This test's objective is to mimic shift creation from the gant view and ensure that the correct behavior is met.
            This test objective is to test the default values when creating a new shift for an employee when provided defaults are within employee's calendar workdays
        """
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-27 00:00:00',
            default_end_datetime='2019-06-27 23:59:59',
            default_resource_id=self.resource_joseph.id)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 27, 9, 0), 'It should be adjusted to employee calendar: 0am -> 9pm')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 27, 18, 0), 'It should be adjusted to employee calendar: 0am -> 18pm')

    def test_create_with_employee_outside_schedule(self):
        """ This test objective is to test the default values when creating a new shift for an employee when provided defaults are not within employee's calendar workdays """
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-26 00:00:00',
            default_end_datetime='2019-06-26 23:59:59',
            default_resource_id=self.resource_joseph.id)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 26, 00, 0), 'It should still be the default start_datetime 0am')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 26, 23, 59, 59), 'It should adjust to employee calendar: 0am -> 9pm')

    def test_create_without_employee(self):
        """ This test objective is to test the default values when creating a new shift when no employee is set """
        self.env.user.tz = 'UTC'
        PlanningSlot = self.env['planning.slot'].with_context(
            tz='UTC',
            default_start_datetime='2019-06-27 00:00:00',
            default_end_datetime='2019-06-27 23:59:59',
            default_resource_id=False)
        defaults = PlanningSlot.default_get(['resource_id', 'start_datetime', 'end_datetime'])
        self.assertEqual(defaults.get('start_datetime'), datetime(2019, 6, 27, 8, 0), 'It should adjust to employee calendar: 0am -> 9pm')
        self.assertEqual(defaults.get('end_datetime'), datetime(2019, 6, 27, 17, 0), 'It should adjust to employee calendar: 0am -> 9pm')

    def test_unassign_employee_with_template(self):
        # we are going to put everybody in EDT, because if the employee has a different timezone from the company this workflow does not work.
        self.env.user.tz = 'America/New_York'
        self.env.user.company_id.resource_calendar_id.tz = 'America/New_York'
        self.slot.template_id = self.template
        self.env.flush_all()
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should set time from template, in user timezone (11am EDT -> 3pm UTC)')

        # simulate public user (no tz)
        self.env.user.tz = False
        self.slot.resource_id = self.resource_janice.id
        self.env.flush_all()
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should adjust to employee timezone')

        self.slot.resource_id = None
        self.assertEqual(self.slot.template_id, self.template, 'It should keep the template')
        self.assertEqual(self.slot.start_datetime, datetime(2019, 6, 27, 15, 0), 'It should reset to company calendar timezone: 11am EDT -> 3pm UTC')

    def test_compute_overlap_count(self):
        self.slot_6_2 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 8, 0),
            'end_datetime': datetime(2019, 6, 2, 17, 0),
        })
        self.slot_6_3 = self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 3, 8, 0),
            'end_datetime': datetime(2019, 6, 3, 17, 0),
        })
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 10, 0),
            'end_datetime': datetime(2019, 6, 2, 12, 0),
        })
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 16, 0),
            'end_datetime': datetime(2019, 6, 2, 18, 0),
        })
        self.env['planning.slot'].create({
            'resource_id': self.resource_bert.id,
            'start_datetime': datetime(2019, 6, 2, 18, 0),
            'end_datetime': datetime(2019, 6, 2, 20, 0),
        })
        self.assertEqual(2, self.slot_6_2.overlap_slot_count, '2 slots overlap')
        self.assertEqual(0, self.slot_6_3.overlap_slot_count, 'no slot overlap')

    def test_compute_datetime_with_template_slot(self):
        """ Test if the start and end datetimes of a planning.slot are correctly computed with the template slot

            Test Case:
            =========
            1) Create a planning.slot.template with start_hours = 11 pm and duration = 3 hours.
            2) Create a planning.slot for one day and add the template.
            3) Check if the start and end dates are on two days and not one.
            4) Check if the allocating hours is equal to the duration in the template.
        """
        self.resource_bert.flexible_hours = True
        template_slot = self.env['planning.slot.template'].create({
            'start_time': 23,
            'duration': 3,
        })

        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2021, 1, 1, 0, 0),
            'end_datetime': datetime(2021, 1, 1, 23, 59),
            'resource_id': self.resource_bert.id,
        })

        slot.write({
            'template_id': template_slot.id,
        })

        self.assertEqual(slot.start_datetime, datetime(2021, 1, 1, 23, 0), 'The start datetime should have the same hour and minutes defined in the template in the resource timezone.')
        self.assertEqual(slot.end_datetime, datetime(2021, 1, 2, 2, 0), 'The end datetime of this slot should be 3 hours after the start datetime as mentionned in the template in the resource timezone.')
        self.assertEqual(slot.allocated_hours, 3, 'The allocated hours of this slot should be the duration defined in the template in the resource timezone.')

    def test_planning_state(self):
        """ The purpose of this test case is to check the planning state """
        self.slot.resource_id = self.employee_bert.resource_id
        self.assertEqual(self.slot.state, 'draft', 'Planning is draft mode.')
        self.slot.action_publish()
        self.assertEqual(self.slot.state, 'published', 'Planning is published.')

    def test_create_working_calendar_period(self):
        """ A default dates should be calculated based on the working calendar of the company whatever the period """
        test = Form(self.env['planning.slot'].with_context(
            default_start_datetime=datetime(2019, 5, 27, 0, 0),
            default_end_datetime=datetime(2019, 5, 27, 23, 59, 59)
        ))
        slot = test.save()
        self.assertEqual(slot.start_datetime, datetime(2019, 5, 27, 8, 0), 'It should adjust to employee calendar: 0am -> 9pm')
        self.assertEqual(slot.end_datetime, datetime(2019, 5, 27, 17, 0), 'It should adjust to employee calendar: 0am -> 9pm')

        # For weeks period
        test_week = Form(self.env['planning.slot'].with_context(
            default_start_datetime=datetime(2019, 6, 23, 0, 0),
            default_end_datetime=datetime(2019, 6, 29, 23, 59, 59)
        ))

        test_week = test_week.save()
        self.assertEqual(test_week.start_datetime, datetime(2019, 6, 24, 8, 0), 'It should adjust to employee calendar: 0am -> 9pm')
        self.assertEqual(test_week.end_datetime, datetime(2019, 6, 28, 17, 0), 'It should adjust to employee calendar: 0am -> 9pm')
