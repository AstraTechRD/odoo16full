# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_compare

from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet
from odoo.exceptions import AccessError

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


@freeze_time(datetime(2021, 4, 1) + timedelta(hours=12, minutes=21))
class TestTimesheetValidation(TestCommonTimesheet, MockEmail):

    def setUp(self):
        super(TestTimesheetValidation, self).setUp()
        today = fields.Date.today()
        self.timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 1",
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': today,
            'unit_amount': 2.0,
        })
        self.timesheet2 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 2",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': today,
            'unit_amount': 3.11,
        })

    def test_timesheet_validation_user(self):
        """ Employee record its timesheets and Officer validate them. Then try to modify/delete it and get Access Error """
        # Officer validate timesheet of 'user_employee' through wizard
        timesheet_to_validate = self.timesheet1 | self.timesheet2
        timesheet_to_validate.with_user(self.user_manager).action_validate_timesheet()

        # Check timesheets 1 and 2 are validated
        self.assertTrue(self.timesheet1.validated)
        self.assertTrue(self.timesheet2.validated)

        # Employee can not modify validated timesheet
        with self.assertRaises(AccessError):
            self.timesheet1.with_user(self.user_employee).write({'unit_amount': 5})
        # Employee can not delete validated timesheet
        with self.assertRaises(AccessError):
            self.timesheet2.with_user(self.user_employee).unlink()

        # Employee can still create new timesheet before the validated date
        last_month = datetime.now() - relativedelta(months=1)
        self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 3",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': last_month,
            'unit_amount': 2.5,
        })

        # Employee can still create timesheet after validated date
        next_month = datetime.now() + relativedelta(months=1)
        timesheet4 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 4",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': next_month,
            'unit_amount': 2.5,
        })
        # And can still update non validated timesheet
        timesheet4.write({'unit_amount': 7})

    def test_timesheet_validation_manager(self):
        """ Officer can see timesheets and modify the ones of other employees """
       # Officer validate timesheet of 'user_employee' through wizard
        timesheet_to_validate = self.timesheet1 | self.timesheet2
        timesheet_to_validate.with_user(self.user_manager).action_validate_timesheet()
        # manager modify validated timesheet
        self.timesheet1.with_user(self.user_manager).write({'unit_amount': 5})

    def _test_next_date(self, now, result, delay, interval):

        def _now(*args, **kwargs):
            return now

        # To allow testing

        patchers = [patch('odoo.fields.Datetime.now', _now)]

        for patcher in patchers:
            self.startPatcher(patcher)

        self.user_manager.company_id.write({
            'timesheet_mail_manager_interval': interval,
            'timesheet_mail_manager_delay': delay,
        })

        self.assertEqual(result, self.user_manager.company_id.timesheet_mail_manager_nextdate)

    def test_timesheet_next_date_reminder_neg_delay(self):

        result = datetime(2020, 4, 23, 8, 8, 15)
        now = datetime(2020, 4, 22, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 4, 30, 8, 8, 15)
        now = datetime(2020, 4, 23, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 4, 24, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 4, 25, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 4, 27, 8, 8, 15)
        now = datetime(2020, 4, 26, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

        result = datetime(2020, 5, 28, 8, 8, 15)
        now = datetime(2020, 4, 27, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 4, 28, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 4, 29, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

        result = datetime(2020, 2, 27, 8, 8, 15)
        now = datetime(2020, 2, 26, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 3, 5, 8, 8, 15)
        now = datetime(2020, 2, 27, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 2, 28, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")
        now = datetime(2020, 2, 29, 8, 8, 15)
        self._test_next_date(now, result, -3, "weeks")

        result = datetime(2020, 2, 26, 8, 8, 15)
        now = datetime(2020, 2, 25, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

        result = datetime(2020, 3, 28, 8, 8, 15)
        now = datetime(2020, 2, 26, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 2, 27, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")
        now = datetime(2020, 2, 28, 8, 8, 15)
        self._test_next_date(now, result, -3, "months")

    def test_minutes_computing_after_timer_stop(self):
        """ Test if unit_amount is updated after stoping a timer """
        Timesheet = self.env['account.analytic.line']
        timesheet_1 = Timesheet.with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': '/',
            'unit_amount': 1,
        })

        # When the timer is greater than 1 minute
        now = datetime.now()
        timesheet_1.with_user(self.user_employee).action_timer_start()
        timesheet_1.with_user(self.user_employee).user_timer_id.timer_start = now - timedelta(minutes=1, seconds=28)
        timesheet_1.with_user(self.user_employee).action_timer_stop()

        self.assertGreater(timesheet_1.unit_amount, 1, 'unit_amount should be greated than his last value')

    def test_timesheet_display_timer(self):
        current_timesheet_uom = self.env.company.timesheet_encode_uom_id

        # self.project_customer.allow_timesheets = True

        self.env.company.timesheet_encode_uom_id = self.env.ref('uom.product_uom_hour')
        self.assertTrue(self.timesheet1.display_timer)

        # Force recompute field
        self.env.company.timesheet_encode_uom_id = self.env.ref('uom.product_uom_day')
        self.timesheet1._compute_display_timer()
        self.assertFalse(self.timesheet1.display_timer)

        self.env.company.timesheet_encode_uom_id = current_timesheet_uom

    def test_add_time_from_wizard(self):
        self.env.user.employee_id = self.env['hr.employee'].create({'user_id': self.env.uid})
        config = self.env["res.config.settings"].create({
                "timesheet_min_duration": 60,
                "timesheet_rounding": 15,
            })
        config.execute()
        wizard_min = self.env['project.task.create.timesheet'].create({
                'time_spent': 0.7,
                'task_id': self.task1.id,
            })
        wizard_round = self.env['project.task.create.timesheet'].create({
                'time_spent': 1.15,
                'task_id': self.task1.id,
            })
        self.assertEqual(wizard_min.with_user(self.env.user).save_timesheet().unit_amount, 1, "The timesheet's duration should be 1h (Minimum Duration = 60').")
        self.assertEqual(wizard_round.with_user(self.env.user).save_timesheet().unit_amount, 1.25, "The timesheet's duration should be 1h15 (Rounding = 15').")

    def test_action_add_time_to_timer_multi_company(self):
        company = self.env['res.company'].create({'name': 'My_Company'})
        self.env['hr.employee'].with_company(company).create({
            'name': 'coucou',
            'user_id': self.user_manager.id,
        })
        self.user_manager.write({'company_ids': [Command.link(company.id)]})
        timesheet = self.env['account.analytic.line'].with_user(self.user_manager).create({'name': 'coucou', 'project_id': self.project_customer.id})
        timesheet.with_user(self.user_manager).action_add_time_to_timer(1)

    def test_working_hours_for_employees(self):
        company = self.env['res.company'].create({'name': 'My_Company'})
        employee = self.env['hr.employee'].with_company(company).create({
            'name': 'Juste Leblanc',
            'user_id': self.user_manager.id,
            'create_date': date(2021, 1, 1),
            'employee_type': 'freelance',  # Avoid searching the contract if hr_contract module is installed before this module.
        })
        employees_grid_data = [{
            'id': employee.id,
            'display_name': employee.name,
            'grid_row_index': 0}]

        working_hours = employee.get_timesheet_and_working_hours_for_employees(employees_grid_data, '2021-12-01', '2021-12-31')
        self.assertEqual(working_hours[employee.id]['units_to_work'], 184.0, "Number of hours should be 23d * 8h/d = 184h")

    def test_timesheet_grid_filter_equal_string(self):
        """Make sure that if you use a filter with (not) equal to,
           there won't be any error with grid view"""
        row_fields = ['project_id', 'task_id']
        col_field = 'date'
        cell_field = 'unit_amount'
        domain = [['employee_id', '=', self.user_employee.employee_id.id],
                  ['project_id', '!=', False]]
        grid_range = {'name': 'week', 'string': 'Week', 'span': 'week', 'step': 'day'}
        orderby = 'project_id,task_id'

        # Filter on project equal a different name, expect 0 row
        new_domain = expression.AND([domain, [('project_id', '=', self.project_customer.name[:-1])]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=grid_range, orderby=orderby)
        self.assertFalse(result['rows'])

        # Filter on project not equal to exact name, expect 0 row
        new_domain = expression.AND([domain, [('project_id', '!=', self.project_customer.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=grid_range, orderby=orderby)
        self.assertFalse(result['rows'])

        # Filter on project_id to make sure there are timesheets
        new_domain = expression.AND([domain, [('project_id', '=', self.project_customer.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=grid_range, orderby=orderby)
        self.assertEqual(len(result['rows']), 2)

        # Filter on task equal to task1, expect timesheet1 (task 1)
        new_domain = expression.AND([domain, [('task_id', '=', self.timesheet1.task_id.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=grid_range, orderby=orderby)
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['values']['project_id'][0], self.timesheet1.project_id.id)
        self.assertEqual(result['rows'][0]['values']['task_id'][0], self.timesheet1.task_id.id)

        # Filter on task not equal to task1, expect timesheet2 (task 2)
        new_domain = expression.AND([domain, [('task_id', '!=', self.timesheet1.task_id.name)]])
        result = self.env['account.analytic.line'].read_grid(row_fields, col_field, cell_field, domain=new_domain, range=grid_range, orderby=orderby)
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['values']['project_id'][0], self.timesheet2.project_id.id)
        self.assertEqual(result['rows'][0]['values']['task_id'][0], self.timesheet2.task_id.id)

    def test_timesheet_manager_reminder(self):
        """ Reminder mail will be sent to both manager Administrator and User Officer to validate the timesheet """
        date = datetime(2022, 3, 3, 8, 8, 15)
        now = datetime(2022, 3, 1, 8, 8, 15)
        self._test_next_date(now, date, -3, "weeks")
        user = self.env.ref('base.user_admin')

        with freeze_time(date), self.mock_mail_gateway():
            self.env['res.company']._cron_timesheet_reminder_manager()
            self.assertEqual(len(self._new_mails.filtered(lambda x: x.res_id == user.employee_id.id)), 1, "An email sent to the 'Administrator Manager'")
            self.assertEqual(len(self._new_mails.filtered(lambda x: x.res_id == self.empl_manager.id)), 1, "An email sent to the 'User Empl Officer'")

    def test_timesheet_employee_reminder(self):
        """ Reminder mail will be sent to each Users' Employee """

        date = datetime(2022, 3, 3, 8, 8, 15)

        Timesheet = self.env['account.analytic.line']
        timesheet_vals = {
            'name': "my timesheet",
            'project_id': self.project_customer.id,
            'date': datetime(2022, 3, 2, 8, 8, 15),
            'unit_amount': 8.0,
        }
        Timesheet.with_user(self.user_employee).create({**timesheet_vals, 'task_id': self.task2.id})
        Timesheet.with_user(self.user_employee2).create({**timesheet_vals, 'task_id': self.task1.id})

        self.user_employee.company_id.timesheet_mail_employee_nextdate = date

        with freeze_time(date), self.mock_mail_gateway():
            self.env['res.company']._cron_timesheet_reminder_employee()
            self.assertEqual(len(self._new_mails.filtered(lambda x: x.res_id == self.empl_employee.id)), 1, "An email sent to the 'User Empl Employee'")
            self.assertEqual(len(self._new_mails.filtered(lambda x: x.res_id == self.empl_employee2.id)), 1, "An email sent to the 'User Empl Employee 2'")

    def test_task_timer_min_duration_and_rounding(self):
        self.env["res.config.settings"].create({
            "timesheet_min_duration": 23,
            "timesheet_rounding": 0,
        }).execute()

        self.task1.action_timer_start()
        act_window_action = self.task1.action_timer_stop()
        wizard = self.env[act_window_action['res_model']].with_context(act_window_action['context']).new()
        self.assertEqual(float_compare(wizard.time_spent, 0.38, 0), 0)
        self.env["res.config.settings"].create({
            "timesheet_rounding": 30,
        }).execute()

        self.task1.action_timer_start()
        act_window_action = self.task1.action_timer_stop()
        wizard = self.env[act_window_action['res_model']].with_context(act_window_action['context']).new()
        self.assertEqual(wizard.time_spent, 0.5)

    def test_timesheet_grid_filter_task_without_project(self):
        """Make sure that a task without project can not be pulled in the domain"""
        row_fields = ['project_id', 'task_id']
        col_field = 'date'
        cell_field = 'unit_amount'
        domain = [['employee_id', '=', self.user_employee.employee_id.id],
                  ['project_id', '!=', False]]
        orderby = 'project_id,task_id'
        # add a task without project
        self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test task without project'
        })
        # look for this task
        new_domain = expression.AND([domain, [('task_id', '=', 'Test task without project')]])
        result = self.env['account.analytic.line'].with_context(group_expand="group_expand").read_grid(row_fields, col_field, cell_field, domain=new_domain, orderby=orderby)
        # there is no error and nothing is in the result because a task witout project can not have timesheets
        self.assertEqual(len(result['rows']), 0)

    def test_adjust_grid(self):
        today_date = fields.Date.today()
        company = self.env['res.company'].create({'name': 'My_Company'})
        self.user_manager.company_ids = self.env.companies
        employee = self.env['hr.employee'].with_company(company).create({
            'name': 'coucou',
            'timesheet_manager_id': self.user_manager.id,
        })

        Timesheet = self.env['account.analytic.line']
        timesheet = Timesheet.with_user(self.user_manager).create({
            'employee_id': employee.id,
            'project_id': self.project_customer.id,
            'date': today_date,
            'unit_amount': 2,
        })
        timesheet.with_user(self.user_manager).action_validate_timesheet()

        column_date = f'{today_date}/{today_date + timedelta(days=1)}'
        Timesheet.adjust_grid([('id', '=', timesheet.id)], 'date', column_date, 'unit_amount', 3.0)

        self.assertEqual(Timesheet.search_count([('employee_id', '=', employee.id)]), 2, "Should create new timesheet instead of updating validated timesheet in cell")
