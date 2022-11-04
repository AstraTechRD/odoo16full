# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestPlanningTimesheetSale(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.manager_company_B._write({
            'employee_type': 'employee',
            'create_date': datetime(2019, 5, 5, 8, 0, 0),
        })

    def test_generate_slot_timesheet_for_non_billable_project(self):
        self.assertFalse(self.project_non_billable.allow_billable, "Project should be non billable")

        self.assertEqual(self.manager_company_B.tz, self.manager_company_B.resource_calendar_id.tz)

        planning_shift = self.env['planning.slot'].create({
            'project_id': self.project_non_billable.id,
            'employee_id': self.manager_company_B.id,
            'resource_id': self.manager_company_B.resource_id.id,
            'allocated_hours': 8,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),  # 6/6/2019 is a tuesday, so a working day
            'end_datetime': datetime(2019, 6, 6, 17, 0, 0),
            'allocated_percentage': 100,
            'state': 'published',
        })
        self.assertFalse(planning_shift.timesheet_ids, "There should be no timesheet linked with current shift")
        planning_shift._action_generate_timesheet()
        self.assertEqual(len(planning_shift.timesheet_ids), 1, "One timesheet should be generated for non billable project")
        self.assertEqual(planning_shift.timesheet_ids.unit_amount, 6, "Timesheet should be generated for the 8 working hours of the employee")

    def test_generate_slot_timesheet_for_billable_project(self):
        self.assertTrue(self.project_global.allow_billable, "Project should be billable")

        planning_shift = self.env['planning.slot'].create({
            'project_id': self.project_global.id,
            'sale_line_id': self.so.order_line.filtered(lambda x: x.product_id == self.product_delivery_timesheet2).id,
            'employee_id': self.manager_company_B.id,
            'resource_id': self.manager_company_B.resource_id.id,
            'allocated_hours': 5,
            'start_datetime': datetime(2019, 6, 6, 8, 0, 0),  # 6/6/2019 is a tuesday, so a working day
            'end_datetime': datetime(2019, 6, 6, 14, 0, 0),
            'allocated_percentage': 100,
            'state': 'published',
        })
        self.assertFalse(planning_shift.timesheet_ids, "There should be no timesheet linked with current shift")
        planning_shift._action_generate_timesheet()
        self.assertEqual(len(planning_shift.timesheet_ids), 1, "One timesheet should be generated for billable project")
        self.assertEqual(planning_shift.timesheet_ids.so_line, planning_shift.sale_line_id, "Generated timesheet should be linked with same so line as shift.")
        self.assertEqual(planning_shift.timesheet_ids.so_line.qty_delivered, planning_shift.timesheet_ids.unit_amount, "Timesheet and so line should have same delivered quantity.")
