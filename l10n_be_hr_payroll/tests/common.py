# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged

class TestPayrollCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollCommon, cls).setUpClass()

        today = date.today()
        cls.belgian_company = cls.env.ref('l10n_be_hr_payroll.res_company_be')

        cls.env.user.company_ids |= cls.belgian_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.belgian_company.ids))

        cls.holiday_leave_types = cls.env['hr.leave.type'].create([{
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'officer',
            'leave_validation_type': 'both',
            'responsible_id': cls.env.ref('base.user_admin').id,
            'request_unit': 'day'
        }])

        cls.holiday_allocations = cls.env['hr.leave.allocation'].create([{
            'name': 'Paid Time Off %s' % year,
            'holiday_status_id': cls.holiday_leave_types.id,
            'number_of_days': 20,
            'holiday_type': 'company',
            'mode_company_id': cls.belgian_company.id,
            'date_from': date(year, 1, 1),
            'date_to': date(year, 12, 31),
        } for year in range(today.year - 2, today.year + 1)])

        cls.resource_calendar = cls.env['resource.calendar'].create({
            'name': 'Test Calendar',
            'company_id': cls.belgian_company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 38,
            'full_time_required_hours': 38
        })

        cls.resource_calendar_mid_time = cls.resource_calendar.copy({
            'name': 'Calendar (Mid-Time)',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
            ]
        })
        cls.resource_calendar_mid_time._onchange_hours_per_day()

        cls.resource_calendar_4_5 = cls.resource_calendar.copy({
            'name': 'Calendar (4 / 5)',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ]
        })
        cls.resource_calendar_4_5._onchange_hours_per_day()

        cls.resource_calendar_9_10 = cls.resource_calendar.copy({
            'name': 'Calendar (9 / 10)',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })
        cls.resource_calendar_9_10._onchange_hours_per_day()

        cls.resource_calendar_30_hours_per_week = cls.resource_calendar.copy({
            'name': 'Calendar 30 Hours/Week',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'})
            ]
        })
        cls.resource_calendar_30_hours_per_week._onchange_hours_per_day()

        address_home_georges = cls.env['res.partner'].create({
            'name': 'Georges',
            'company_id': cls.belgian_company.id,
            'type': 'private',
            'country_id': cls.env.ref('base.be').id
        })

        cls.employee_georges = cls.env['hr.employee'].create({
            'name': 'Georges',
            'address_home_id': address_home_georges.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.belgian_company.id,
            'marital': "single",
            'spouse_fiscal_status': "without_income",
            'disabled': False,
            'disabled_spouse_bool': False,
            'resident_bool': False,
            'disabled_children_number': 0,
            'other_dependent_people': False,
            'other_senior_dependent': 0,
            'other_disabled_senior_dependent': 0,
            'other_juniors_dependent': 0,
            'other_disabled_juniors_dependent': 0,
            'has_bicycle': False
        })

        first_contract_georges = cls.env['hr.contract'].create({
            'name': "Georges's contract",
            'employee_id': cls.employee_georges.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.belgian_company.id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': date(today.year - 2, 1, 1),
            'date_end': date(today.year - 2, 12, 31),
            'wage': 2500.0,
            'hourly_wage': 0.0,
            'commission_on_target': 0.0,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'has_laptop': False,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip': False,
            'ip_wage_rate': 25.0,
            'time_credit': False,
            'fiscal_voluntarism': False,
            'fiscal_voluntary_rate': 0.0
        })

        cls.georges_contracts = first_contract_georges

        cls.georges_contracts |= first_contract_georges.copy({
            'date_start': date(today.year - 1, 1, 1),
            'date_end': date(today.year - 1, 5, 31),
            'resource_calendar_id': cls.resource_calendar_mid_time.id,
            'wage': 1250
        })

        cls.georges_contracts |= first_contract_georges.copy({
            'date_start': date(today.year - 1, 6, 1),
            'date_end': date(today.year - 1, 8, 31),
        })

        cls.georges_contracts |= first_contract_georges.copy({
            'date_start': date(today.year - 1, 9, 1),
            'date_end': date(today.year - 1, 12, 31),
            'resource_calendar_id': cls.resource_calendar_4_5.id,
            'wage': 2500 * 4 / 5
        })

        cls.georges_contracts.write({'state': 'close'})  # By default, the state is 'draft' when we create a new contract

        contract = first_contract_georges.copy({
            'date_start': date(today.year, 1, 1),
            'date_end': False,
            'resource_calendar_id': cls.resource_calendar_4_5.id,
            'wage': 2500 * 4 / 5
        })
        contract.write({'state': 'open'})  # By default, the state is 'draft' when we create a new contract
        cls.georges_contracts |= contract

        address_home_john = cls.env['res.partner'].create({
            'name': 'John Doe',
            'company_id': cls.belgian_company.id,
            'type': 'private',
            'country_id': cls.env.ref('base.be').id
        })

        cls.employee_john = cls.employee_georges.copy({
            'name': 'John Doe',
            'address_home_id': address_home_john.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'contract_ids': []
        })

        first_contract_john = first_contract_georges.copy({
            'name': "John's Contract",
            'employee_id': cls.employee_john.id,
            'resource_calendar_id': cls.resource_calendar.id
        })

        cls.john_contracts = first_contract_john

        cls.john_contracts |= first_contract_john.copy({
            'date_start': date(today.year - 1, 1, 1),
            'date_end': date(today.year - 1, 3, 31)
        })

        cls.john_contracts |= first_contract_john.copy({
            'date_start': date(today.year - 1, 4, 1),
            'date_end': date(today.year - 1, 6, 30),
            'resource_calendar_id': cls.resource_calendar_9_10.id,
            'time_credit': True
        })

        cls.john_contracts |= first_contract_john.copy({
            'date_start': date(today.year - 1, 7, 1),
            'date_end': date(today.year - 1, 9, 30),
            'resource_calendar_id': cls.resource_calendar_4_5.id,
            'time_credit': True
        })

        cls.john_contracts.write({'state': 'close'})  # By default, the state is 'draft' when we create a new contract

        contract = first_contract_john.copy({
            'date_start': date(today.year - 1, 10, 1),
            'date_end': False,
            'resource_calendar_id': cls.resource_calendar_mid_time.id,
            'time_credit': True
        })
        contract.write({'state': 'open'})  # By default, the state is 'draft' when we create a new contract

        cls.john_contracts |= contract

        address_home_a = cls.env['res.partner'].create({
            'name': 'A',
            'company_id': cls.belgian_company.id,
            'type': 'private',
            'country_id': cls.env.ref('base.be').id
        })

        cls.employee_a = cls.employee_georges.copy({
            'name': 'A',
            'address_home_id': address_home_a.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'contract_ids': []
        })

        first_contract_a = first_contract_georges.copy({
            'name': "A's Contract",
            'employee_id': cls.employee_a.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_start': date(today.year - 1, 1, 1),
            'date_end': False
        })

        first_contract_a.write({'state': 'open'})

        cls.a_contracts = first_contract_a

        address_home_test = cls.env['res.partner'].create({
            'name': 'Employee Test',
            'company_id': cls.belgian_company.id,
            'type': 'private',
            'country_id': cls.env.ref('base.be').id
        })

        cls.employee_test = cls.employee_georges.copy({
            'name': 'Employee Test',
            'address_home_id': address_home_test.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'contract_ids': []
        })

        first_contract_test = first_contract_georges.copy({
            'name': "Employee Test's Contract",
            'employee_id': cls.employee_test.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_start': date(2017, 1, 1),
            'date_end': False
        })

        first_contract_test.write({'state': 'open'})

        cls.test_contracts = first_contract_test
