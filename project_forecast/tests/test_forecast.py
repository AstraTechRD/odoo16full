# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from .common import TestCommonForecast


@tagged('-at_install', 'post_install')
class TestForecastCreationAndEditing(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super(TestForecastCreationAndEditing, cls).setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.Datetime.now)
        with freeze_time('2019-1-1'):
            cls.setUpEmployees()
            cls.setUpProjects()

        # planning_shift on one day (planning mode)
        cls.slot = cls.env['planning.slot'].create({
            'project_id': cls.project_opera.id,
            'resource_id': cls.employee_bert.resource_id.id,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),  # 6/6/2019 is a tuesday, so a working day
            'end_datetime': datetime(2019, 6, 6, 17, 0, 0),
        })

    def test_creating_a_planning_shift_allocated_hours_are_correct(self):
        self.assertEqual(self.slot.allocated_hours, 8.0, 'resource hours should be a full workday')

        self.slot.write({'allocated_percentage': 50})
        self.assertEqual(self.slot.allocated_hours, 4.0, 'resource hours should be a half duration')

        # self.slot on non working days
        values = {
            'allocated_percentage': 100,
            'start_datetime': datetime(2019, 6, 2, 8, 0, 0),  # sunday morning
            'end_datetime': datetime(2019, 6, 2, 17, 0, 0)  # sunday evening, same sunday, so employee is not working
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 0, 'resource hours should be a full day working hours')

        # self.slot on multiple days (forecast mode)
        values = {
            'allocated_percentage': 100,   # full week
            'start_datetime': datetime(2019, 6, 3, 0, 0, 0),  # 6/3/2019 is a monday
            'end_datetime': datetime(2019, 6, 8, 23, 59, 0)  # 6/8/2019 is a sunday, so we have a full week
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 40, 'resource hours should be a full week\'s available hours')

    def test_creating_a_planning_shift_with_flexible_hours_allocated_hours_are_correct(self):
        self.employee_bert.resource_id.flexible_hours = True
        self.assertEqual(self.slot.allocated_hours, 8.0, 'resource hours should be a full workday')

        self.slot.write({'allocated_percentage': 50})
        self.assertEqual(self.slot.allocated_hours, 4.0, 'resource hours should be a half duration')

        # self.slot on non working days
        values = {
            'allocated_percentage': 100,
            'start_datetime': datetime(2019, 6, 2, 8, 0, 0),  # sunday morning
            'end_datetime': datetime(2019, 6, 2, 17, 0, 0)  # sunday evening, same sunday, so employee is not working
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 8, 'resource hours should be a full day working hours')

        # self.slot on multiple days (forecast mode)
        values = {
            'allocated_percentage': 100,   # full week
            'start_datetime': datetime(2019, 6, 3, 0, 0, 0),  # 6/3/2019 is a monday
            'end_datetime': datetime(2019, 6, 8, 23, 0, 0)  # 6/8/2019 is a sunday, so we have a full week
        }
        self.slot.write(values)

        self.assertEqual(self.slot.allocated_hours, 8 * 6, 'allocated hours should be equal to the real period since the resource has a flexible hours.')
