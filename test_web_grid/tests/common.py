# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestWebGrid(common.SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestWebGrid, cls).setUpClass()

        cls.project = cls.env['test.web.grid.project'].create({
            'name': 'DragonballZ',
        })

        cls.task = cls.env['test.web.grid.task'].create({
            'name': 'Kill Freeza',
            'project_id': cls.project.id,
        })

        cls.employee = cls.env['test.web.grid.employee'].create({
            'name': 'Kakarot',
        })

        # DateTime Object
        cls.grid_obj_1 = cls.env['test.web.grid'].create({
            'employee_id': cls.employee.id,
            'project_id': cls.project.id,
            'task_id': cls.task.id,
            'resource_hours': 3,
            'start_datetime': "2019-06-14 11:30:00",
        })

        # For checking freeze cell of datetime object (readonly)
        cls.grid_obj_1_validated = cls.env['test.web.grid'].create({
            'employee_id': cls.employee.id,
            'project_id': cls.project.id,
            'task_id': cls.task.id,
            'start_datetime': "2019-06-19 11:30:00",
            'resource_hours': 9,
            'validated': True,
        })

        # Date Object
        cls.grid_obj_2 = cls.env['test.web.grid'].create({
            'employee_id': cls.employee.id,
            'project_id': cls.project.id,
            'task_id': cls.task.id,
            'resource_hours': 4,
            'start_date': "2019-06-04",
        })

        # For checking freeze cell of date object(readonly)
        cls.grid_obj_2_validated = cls.env['test.web.grid'].create({
            'employee_id': cls.employee.id,
            'project_id': cls.project.id,
            'task_id': cls.task.id,
            'resource_hours': 10,
            'start_date': "2019-06-10",
            'validated': True,
        })

        cls.grid_obj_3 = cls.env['test.web.grid'].create({
            'employee_id': cls.employee.id,
            'project_id': False,  # used to check if the `read_grid_grouped` using this field as section field does not crash.
            'task_id': cls.task.id,
            'resource_hours': 10,
            'start_date': "2019-06-10",
        })

        # Combinations of different ranges
        cls.range_day = {'name': 'days', 'string': 'Day', 'span': 'month', 'step': 'day'}

        cls.range_week = {'name': "week", 'string': 'Week', 'span': 'week', 'step': 'day'}
        cls.range_week_2 = {'name': "week", 'string': 'Week', 'span': 'month', 'step': 'week'}

        cls.range_month = {'name': 'months', 'string': 'Month', 'span': 'year', 'step': 'month'}
