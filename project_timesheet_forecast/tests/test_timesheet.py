# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import date, datetime

from odoo import fields
from odoo.addons.project_forecast.tests.common import TestCommonForecast
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestPlanningTimesheet(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.setUpEmployees()
        cls.setUpProjects()
        cls.employee_bert.write({
            'employee_type': 'freelance',
            'create_date': datetime(2019, 5, 6, 8, 0, 0),
        })

    def test_no_auto_genertaed_timesheet_in_future(self):
        with self._patch_now('2019-06-06 18:00:00'):
            self.project_opera.write({'allow_timesheets': True})

            planning_shift = self.env['planning.slot'].create({
                'project_id': self.project_opera.id,
                'employee_id': self.employee_bert.id,
                'resource_id': self.resource_bert.id,
                'allocated_hours': 16,
                'start_datetime': datetime(2019, 6, 6, 8, 0, 0),  # 6/6/2019 is a thursday, so a working day
                'end_datetime': datetime(2019, 6, 7, 17, 0, 0),
                'allocated_percentage': 100,
                'state': 'published',
            })
            self.assertFalse(planning_shift.timesheet_ids, "There should be no timesheet linked with current shift.")
            planning_shift._action_generate_timesheet()
            self.assertEqual(len(planning_shift.timesheet_ids), 1, "One timesheet should be generated for current shift.")
            self.assertEqual(planning_shift.timesheet_ids.date, fields.Datetime.today().date(), "Generated timesheet date should be today.")
            self.assertEqual(planning_shift.timesheet_ids.unit_amount, 8, "Timesheet should be generated for the 8 working hours of the employee")
            self.assertFalse(planning_shift.timesheet_ids.filtered(lambda x: x.date > date(2019, 6, 6)), "No timesheet should be generated in the future.")

    def test_custom_time_on_auto_generated_timesheet(self):
        with self._patch_now('2019-06-07 18:00:00'):
            self.project_opera.write({'allow_timesheets': True})

            planning_shift = self.env['planning.slot'].create({
                'project_id': self.project_opera.id,
                'employee_id': self.employee_bert.id,
                'resource_id': self.resource_bert.id,
                'allocated_hours': 37,
                'start_datetime': datetime(2019, 6, 3, 10, 0, 0),  # 3/6/2019 is a monday, so a working day
                'end_datetime': datetime(2019, 6, 7, 16, 0, 0),    # 7/6/2019 is a friday, so a working day
                'allocated_percentage': 100,
                'state': 'published',
            })
            self.assertFalse(planning_shift.timesheet_ids, "There should be no timesheet linked with current shift.")
            planning_shift._action_generate_timesheet()
            self.assertEqual(len(planning_shift.timesheet_ids), 5, "Five days timesheet should be generated for current shift.")
            self.assertEqual(planning_shift.timesheet_ids.filtered(lambda x: x.date == date(2019, 6, 3)).unit_amount, 6, "There should be a 6-hour timesheet on the first day of the shift.")
            self.assertEqual(planning_shift.timesheet_ids.filtered(lambda x: x.date == date(2019, 6, 4)).unit_amount, 8, "There should be a 8-hour timesheet on the second day of the shift.")
            self.assertEqual(planning_shift.timesheet_ids.filtered(lambda x: x.date == date(2019, 6, 7)).unit_amount, 7, "There should be a 7-hour timesheet on the last day of the shift.")


class TestPlanningTimesheetView(TestCommonTimesheet):
    def test_get_view_timesheet_encode_uom(self):
        """ Test the label of timesheet time spent fields according to the company encoding timesheet uom """
        self.assert_get_view_timesheet_encode_uom([
            (
                'project_timesheet_forecast.project_timesheet_forecast_report_view_pivot',
                '//field[@name="planned_hours"]',
                [None, 'Planned Days']
            ),
        ])
