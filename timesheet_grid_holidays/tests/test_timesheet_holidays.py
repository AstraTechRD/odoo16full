# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, SUPERUSER_ID
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTimesheetGridHolidays(TestCommonTimesheet):

    def test_overtime_calcution_timesheet_holiday_flow(self):
        """ Employee's leave is not calculated as overtime hours when employee is on time off."""

        HrEmployee = self.env['hr.employee']
        employees_grid_data = [{'id': self.empl_employee.id}]
        self.empl_employee.write({
            'create_date': date(2021, 1, 1),
            'employee_type': 'freelance',  # Avoid searching the contract if hr_contract module is installed before this module.
        })
        start_date = '2021-10-04'
        end_date = '2021-10-09'
        result = HrEmployee.get_timesheet_and_working_hours_for_employees(employees_grid_data, start_date, end_date)
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 40, "Employee weekly working hours should be 40.")
        self.assertEqual(result[self.empl_employee.id]['worked_hours'], 0.0, "Employee's working hours should be None.")

        leave_start_datetime = datetime(2021, 10, 5, 7, 0, 0, 0)  # this is Tuesday
        leave_end_datetime = leave_start_datetime + relativedelta(days=1)
        # all company have those internal project/task (created by default)
        internal_project = self.env.company.internal_project_id
        internal_task_leaves = self.env.company.leave_timesheet_task_id
        hr_leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': internal_project.id,
            'timesheet_task_id': internal_task_leaves.id,
        })
        HrLeave = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        # employee creates a leave request
        number_of_days = (leave_end_datetime - leave_start_datetime).days
        holiday = HrLeave.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type.id,
            'date_from': leave_start_datetime,
            'date_to': leave_end_datetime,
            'number_of_days': number_of_days,
        })
        holiday.with_user(SUPERUSER_ID).action_validate()
        result = HrEmployee.get_timesheet_and_working_hours_for_employees(employees_grid_data, start_date, end_date)
        self.assertTrue(len(holiday.timesheet_ids) > 0, 'Timesheet entry should be created in Internal project for time off.')
        # working hours for employee after leave creations
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 32, "Employee's weekly units of work after the leave creation should be 32.")
        self.assertEqual(result[self.empl_employee.id]['worked_hours'], 0.0, "Employee's working hours shouldn't be altered after the leave creation.")

        # Timesheet created for same project
        timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 1",
            'project_id': internal_project.id,
            'date': '2021-10-04',
            'unit_amount': 8.0,
        })
        timesheet1.with_user(self.user_manager).action_validate_timesheet()
        result = HrEmployee.get_timesheet_and_working_hours_for_employees(employees_grid_data, start_date, end_date)
        # working hours for employee after Timesheet creations
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 32, "Employee's one week units of work after the Timesheet creation should be 32.")

    def test_adjust_grid_holiday(self):
        Requests = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        hr_leave_type_with_ts = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': self.env.company.internal_project_id.id,
            'timesheet_task_id': self.env.company.leave_timesheet_task_id.id,
        })
        # employee creates a leave request
        holiday = Requests.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type_with_ts.id,
            'date_from': datetime(2018, 2, 5, 7, 0, 0, 0),
            'date_to': datetime(2018, 2, 5, 8, 0, 0, 0),
            'number_of_days': 1,
        })
        # validate leave request and create timesheet
        holiday.with_user(SUPERUSER_ID).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), 1)

        # create timesheet via adjust_grid
        today_date = fields.Date.today()
        column_date = f'{today_date}/{today_date + timedelta(days=1)}'
        self.env['account.analytic.line'].with_user(SUPERUSER_ID).adjust_grid([('id', '=', holiday.timesheet_ids.id)], 'date', column_date, 'unit_amount', 3.0)

        timesheets = self.env['account.analytic.line'].search([('employee_id', '=', self.empl_employee.id), ('unit_amount', 'in', [1, 3])])

        self.assertTrue((not timesheets[0].holiday_id) ^ (not timesheets[1].holiday_id), "The new timesheet should not be linked to a leave request")
