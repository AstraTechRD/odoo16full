# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.exceptions import ValidationError, UserError
from odoo.fields import Datetime
from odoo.tests.common import tagged
from odoo.addons.hr_payroll_holidays.tests.common import TestPayrollHolidaysBase

from dateutil.relativedelta import relativedelta

@tagged('payroll_holidays_defer')
class TestTimeoffDefer(TestPayrollHolidaysBase):

    def test_no_defer(self):
        #create payslip -> waiting or draft
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_to_defer(self):
        #create payslip
        payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip',
            'employee_id': self.emp.id,
        })

        # Puts the payslip to draft/waiting
        payslip.compute_sheet()
        payslip.action_payslip_done()

        #create a time off for our employee, validating it now should put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

    def test_multi_payslip_defer(self):
        #A leave should only be set to defer if ALL colliding with the time period of the time off are in a done state
        # it should not happen if a payslip for that time period is still in a waiting state

        #create payslip -> waiting
        waiting_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip draft',
            'employee_id': self.emp.id,
        })
        #payslip -> done
        done_payslip = self.env['hr.payslip'].create({
            'name': 'Donald Payslip done',
            'employee_id': self.emp.id,
        })

        # Puts the waiting payslip to draft/waiting
        waiting_payslip.compute_sheet()
        # Puts the done payslip to the done state
        done_payslip.compute_sheet()
        done_payslip.action_payslip_done()

        #create a time off for our employee, validating it now should not put it as to_defer
        leave = self.env['hr.leave'].create({
            'name': 'Golf time',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': (Datetime.today() + relativedelta(day=13)),
            'date_to': (Datetime.today() + relativedelta(day=16)),
            'number_of_days': 3,
        })
        leave.action_approve()

        self.assertNotEqual(leave.payslip_state, 'blocked', 'Leave should not be to defer')

    def test_payslip_paid_past(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })

        payslip.compute_sheet()
        self.assertEqual(payslip.state, 'verify')

        self.env['hr.leave'].with_user(self.vlad).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': '2022-01-12',
            'date_to': '2022-01-12',
            'number_of_days': 1,
        })
        payslip.action_payslip_done()

        # A Simple User can't request a leave if a payslip is paid
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.vlad).create({
                'name': 'Tennis',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.emp.id,
                'date_from': '2022-01-19',
                'date_to': '2022-01-19',
                'number_of_days': 1,
            })

        # Check overlapping periods with no payslip
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.vlad).create({
                'name': 'Tennis',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.emp.id,
                'date_from': '2022-01-31',
                'date_to': '2022-02-01',
                'number_of_days': 2,
            })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.vlad).create({
                'name': 'Tennis',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.emp.id,
                'date_from': '2021-01-31',
                'date_to': '2022-01-03',
                'number_of_days': 2,
            })

        # But a time off officer can
        self.env['hr.leave'].with_user(self.joseph).create({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'date_from': '2022-01-19',
            'date_to': '2022-01-19',
            'number_of_days': 1,
        })

    def test_report_to_next_month(self):
        self.emp.contract_ids._generate_work_entries(datetime(2022, 1, 1), datetime(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 31),
            'request_date_to': date(2022, 1, 31),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 1,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        leave.action_report_to_next_month()
        reported_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2022-02-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2022-02-28'), datetime.max.time()))
        ])
        self.assertEqual(reported_work_entries[0].date_start, datetime(2022, 2, 1, 7, 0))
        self.assertEqual(reported_work_entries[0].date_stop, datetime(2022, 2, 1, 11, 0))
        self.assertEqual(reported_work_entries[1].date_start, datetime(2022, 2, 1, 12, 0))
        self.assertEqual(reported_work_entries[1].date_stop, datetime(2022, 2, 1, 16, 0))

    def test_report_to_next_month_overlap(self):
        # If the time off overlap over 2 months, only report the exceeding part from january
        self.emp.contract_ids._generate_work_entries(datetime(2022, 1, 1), datetime(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 31),
            'request_date_to': date(2022, 2, 2),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 3,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        leave.action_report_to_next_month()
        reported_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2022-02-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2022-02-28'), datetime.max.time()))
        ])
        self.assertEqual(len(reported_work_entries), 6)
        self.assertEqual(list(set(we.date_start.day for we in reported_work_entries)), [1, 2, 3])
        self.assertEqual(reported_work_entries[0].date_start, datetime(2022, 2, 1, 7, 0))
        self.assertEqual(reported_work_entries[0].date_stop, datetime(2022, 2, 1, 11, 0))
        self.assertEqual(reported_work_entries[1].date_start, datetime(2022, 2, 1, 12, 0))
        self.assertEqual(reported_work_entries[1].date_stop, datetime(2022, 2, 1, 16, 0))

    def test_report_to_next_month_not_enough_days(self):
        # If the time off contains too many days to be reported to next months, raise
        self.emp.contract_ids._generate_work_entries(datetime(2022, 1, 1), datetime(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 1),
            'request_date_to': date(2022, 1, 31),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 21, # February only contains 20 open days
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        with self.assertRaises(UserError):
            leave.action_report_to_next_month()

    def test_report_to_next_month_long_time_off(self):
        # If the time off overlap over more than 2 months, raise
        self.emp.contract_ids._generate_work_entries(datetime(2022, 1, 1), datetime(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'employee_id': self.emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2022, 1, 1),
            'request_date_to': date(2022, 3, 10),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 21,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))
        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        with self.assertRaises(UserError):
            leave.action_report_to_next_month()

    def test_report_to_next_month_half_days(self):
        self.leave_type.request_unit = 'half_day'
        self.emp.contract_ids._generate_work_entries(datetime(2022, 1, 1), datetime(2022, 2, 28))
        payslip = self.env['hr.payslip'].create({
            'name': 'toto payslip',
            'employee_id': self.emp.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-31',
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')

        leave = self.env['hr.leave'].new({
            'name': 'Tennis',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.emp.id,
            'request_date_from': date(2022, 1, 31),
            'request_date_to': date(2022, 1, 31),
            'request_unit_half': True,
            'request_date_from_period': 'am',
            'number_of_days': 0.5,
        })
        leave._compute_date_from_to()
        leave = self.env['hr.leave'].create(leave._convert_to_write(leave._cache))

        leave.action_validate()
        self.assertEqual(leave.payslip_state, 'blocked', 'Leave should be to defer')

        leave.action_report_to_next_month()
        reported_work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.emp.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft'),
            ('work_entry_type_id', '=', self.leave_type.work_entry_type_id.id),
            ('date_start', '>=', Datetime.to_datetime('2022-02-01')),
            ('date_stop', '<=', datetime.combine(Datetime.to_datetime('2022-02-28'), datetime.max.time()))
        ])
        self.assertEqual(len(reported_work_entries), 1)
        self.assertEqual(reported_work_entries[0].date_start, datetime(2022, 2, 1, 7, 0))
        self.assertEqual(reported_work_entries[0].date_stop, datetime(2022, 2, 1, 11, 0))
