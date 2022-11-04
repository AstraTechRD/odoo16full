# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import date, datetime

from odoo.addons.project_forecast.tests.common import TestCommonForecast


class TestPlanningContractTimesheet(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpEmployees()
        cls.setUpProjects()

        cls.employee_bert.employee_type = 'employee'
        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
            ],
        })
        cls.calendar_35h._onchange_hours_per_day()  # update hours/day

        cls.contract_cdd = cls.env['hr.contract'].create({
            'date_start': date(2021, 9, 1),
            'date_end': date(2021, 10, 31),
            'name': 'First CDD Contract for Bert',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': cls.employee_bert.id,
            'state': 'close',
        })
        cls.contract_cdi = cls.env['hr.contract'].create({
            'date_start': date(2021, 11, 1),
            'name': 'CDI Contract for Bert',
            'resource_calendar_id': cls.employee_bert.resource_calendar_id.id,
            'wage': 5000.0,
            'employee_id': cls.employee_bert.id,
            'state': 'open',
            'kanban_state': 'done',
        })

    def test_auto_generated_timesheet_based_contract_resource_calendar(self):
        self.project_opera.write({'allow_timesheets': True})

        planning_shift = self.env['planning.slot'].create({
            'project_id': self.project_opera.id,
            'employee_id': self.employee_bert.id,
            'resource_id': self.resource_bert.id,
            'allocated_hours': 24,
            'start_datetime': datetime(2021, 10, 29, 8, 0, 0), # Friday
            'end_datetime': datetime(2021, 11, 2, 17, 0, 0), # Tuesday
            'allocated_percentage': 100,
            'state': 'published',
        })
        self.assertFalse(planning_shift.timesheet_ids, "There should be no timesheet linked with current shift.")
        planning_shift._action_generate_timesheet()
        self.assertEqual(len(planning_shift.timesheet_ids), 3, "Three days timesheet should be generated for current shift.")
        self.assertEqual(planning_shift.timesheet_ids.filtered(lambda x: x.date == date(2021, 10, 29)).unit_amount, 7, "There should be a 7-hour timesheet as per 35 hours calendar on the first day of the shift.")
        self.assertEqual(planning_shift.timesheet_ids.filtered(lambda x: x.date == date(2021, 11, 1)).unit_amount, 8, "There should be a 8-hour timesheet as per 40 hours calendar on the second day of the shift.")
        self.assertEqual(planning_shift.timesheet_ids.filtered(lambda x: x.date == date(2021, 11, 2)).unit_amount, 8, "There should be a 8-hour timesheet as per 40 hours calendar on the last day of the shift.")
