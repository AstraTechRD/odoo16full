# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import datetime
from collections import OrderedDict

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare
from odoo.tests import common, tagged


@tagged('post_install', '-at_install', 'examples')
class TestExamples(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].country_id = cls.env.ref('base.be')

        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'full_time_required_hours': 38,
            'attendance_ids': [
                (5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ],
        })
        cls.classic_38h_calendar = cls.env.company.resource_calendar_id

        cls.Payslip = cls.env['hr.payslip']

        cls.env.user.tz = 'Europe/Brussels'

        cls.leave_type_bank_holidays = cls.env['hr.leave.type'].create({
            'name': 'Bank Holiday',
            'request_unit': 'hour',
            'requires_allocation': 'no',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_leave').id,
        })
        cls.leave_type_unpaid = cls.env['hr.leave.type'].create({
            'name': 'Unpaid',
            'request_unit': 'hour',
            'requires_allocation': 'no',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id,
        })
        cls.leave_type_small_unemployment = cls.env['hr.leave.type'].create({
            'name': 'Small Unemployment',
            'request_unit': 'hour',
            'requires_allocation': 'no',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_small_unemployment').id,
        })

    def case_test(self, payslip_results, employee_values, payslip_values=None, contract_values=None, holidays_values=None, car_values=None, car_contract_values=None):
        """
            payslip_results is a dict with key = line.code and value = line.value
            Employee_values is either a dict to pass to create or an xmlid
            Payslip_values is a dict to pass to create
            Contract_values is a dict to pass to create
        """
        if holidays_values is None:
            holidays_values = []

        # Setup the employee

        if isinstance(employee_values, dict):
            employee = self.env['hr.employee'].create(dict(
                employee_values,
                company_id=self.env.company.id))
        else:
            employee = self.env.ref(employee_values)
            # Reset work entry generation
            self.env['hr.work.entry'].search([('employee_id', '=', employee.id)]).unlink()
            employee.contract_id.date_generated_from = datetime.datetime.now()
            employee.contract_id.date_generated_to = datetime.datetime.now()
        employee.resource_calendar_id.tz = "Europe/Brussels"

        # Setup the car, if specified
        if car_values is not None:
            car = self.env['fleet.vehicle'].create(car_values)
            contract_values.update({
                'transport_mode_car': True,
                'car_id': car.id,
            })

        if car_contract_values is not None:
            car.log_contracts.write(car_contract_values)

        # Setup the contract, use the above employee
        if isinstance(contract_values, dict):
            contract_values = dict(contract_values,
                                   structure_type_id=payslip_values.get('struct_id').type_id.id,
                                   employee_id=employee.id)
            contract_id = self.env['hr.contract'].create(contract_values)
            if contract_id.holidays:
                contract_id.wage_on_signature = contract_id.wage_with_holidays
            contract_id.resource_calendar_id.tz = "Europe/Brussels"
            contract_id.write({'state': 'open'})

        # Setup the holidays, use the above employee and contract
        holidays = self.env['hr.leave']
        for holiday_values in holidays_values:
            if isinstance(holiday_values, dict):
                holiday_values.update({
                    'employee_id': employee.id,
                    'request_unit_hours': True,
                })
                holiday = self.env['hr.leave'].new(holiday_values)
                holiday._compute_date_from_to()
                holidays |= self.env['hr.leave'].create(holiday._convert_to_write(holiday._cache))
        holidays.action_validate()
        self.env['hr.work.entry'].search([('leave_id', 'in', holidays.ids)]).action_validate()

        # Generate the poubelles
        if 'date_from' in payslip_values and 'date_to' in payslip_values:
            work_entries = employee.contract_id._generate_work_entries(payslip_values['date_from'], payslip_values['date_to'])
            work_entries.action_validate()

        # Setup the payslip
        payslip_values = dict(payslip_values or {},
                              contract_id=employee.contract_id,
                              company_id=self.env.company.id,
                              name='Test Payslip')

        payslip_id = self.Payslip.new(self.Payslip.default_get(self.Payslip.fields_get()))
        payslip_id.update(payslip_values)

        payslip_id.employee_id = employee.id
        values = payslip_id._convert_to_write(payslip_id._cache)
        payslip_id = self.Payslip.create(values)

        # Compute the payslip
        payslip_id.compute_sheet()

        # Check that all is right
        error = False
        result = ""
        line_values = payslip_id._get_line_values(payslip_results.keys())
        for code, value in payslip_results.items():
            payslip_value = line_values[code][payslip_id.id]['total']
            if float_compare(payslip_value, value, precision_rounding=payslip_id.currency_id.rounding):
                error = True
                result += "Code: %s, Expected: %s, Reality: %s\n" % (code, value, payslip_value)
        self.assertEqual(error, False, 'The payslip values are incorrect for the following codes:\n' + result)

        # Confirm the payslip
        payslip_id.action_payslip_done()

    def test_cdi_laurie_poiret(self):
        values = OrderedDict([
            ('BASIC', 2650.00),
            ('ATN.INT', 5.00),
            ('ATN.MOB', 4.00),
            ('SALARY', 2659.00),
            ('ONSS', -347.53),
            ('ATN.CAR', 149.29),
            ('GROSS', 2460.75),
            ('P.P', -559.87),
            ('ATN.CAR.2', -149.29),
            ('ATN.INT.2', -5.00),
            ('ATN.MOB.2', -4.00),
            ('M.ONSS', -23.66),
            ('MEAL_V_EMP', -21.80),
            ('REP.FEES', 150.00),
            ('NET', 1847.14),
        ])
        payslip = {
            'date_from': datetime.date(2019, 2, 1),
            'date_to': datetime.date(2019, 2, 28),
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
        }
        lap_address = self.env['res.partner'].create({
            'name': 'Laurie Poiret',
            'street': '58 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': self.env.ref("base.be").id,
            'phone': '+0032476543210',
            'email': 'laurie.poiret@example.com',
            'company_id': self.env.company.id,
        })
        employee_vals = {
            'name': 'Laurie Poiret',
            'marital': 'single',
            'resource_calendar_id': self.classic_38h_calendar.id,
            'company_id': self.env.company.id,
        }
        car_vals = {
            'model_id': self.env.ref("fleet.model_a3").id,
            'license_plate': '1-JFC-095',
            'acquisition_date': time.strftime('%Y-01-01'),
            'co2': 88,
            'driver_id': lap_address.id,
            'car_value': 38000,
            'company_id': self.env.company.id,
        }
        contract_vals = {
            'name': 'CDI - Laurie Poiret - Experienced Developer',
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'wage': 2650,
            'wage_on_signature': 2650,
            'commission_on_target': 0.0,
            'transport_mode_car': True,
            'new_car': False,
            'state': 'open',
            'ip_wage_rate': 0,
            'ip': False,
            'date_start': datetime.date(2019, 1, 1),
            'company_id': self.env.company.id,
            'resource_calendar_id': self.env.company.resource_calendar_id.id,
        }

        # Set the start date to January 2019 to take into account on payslip
        self.case_test(values, employee_vals, payslip_values=payslip, contract_values=contract_vals, car_values=car_vals)

    def test_example(self):
        values = OrderedDict([
            ('BASIC', 2500.0),
        ])
        employee = {
            'name': 'Roger',
        }
        contract = {
            'name': 'Contract For Roger',
            'date_start': datetime.date(2019, 1, 1),
            'wage': 2500,
            'wage_on_signature': 2500,
        }
        payslip = {
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
        }
        self.case_test(values, employee, payslip_values=payslip, contract_values=contract)

    # 4 hours unpaid, 2 days leave, no atn and no car
    # Note: The IP is not the same as in the reference payslip, as it
    # was incorrectly computed by SDWorx during 2018

    def test_without_car_without_atn(self):
        values = OrderedDict([
            ('BASIC', 3655.32),
            ('ATN.INT', 0.00),
            ('ATN.MOB', 0.0),
            ('SALARY', 3655.32),
            ('ONSS', -477.75),
            ('ATN.CAR', 0),
            ('GROSSIP', 3177.57),
            ('IP.PART', -913.83),
            ('GROSS', 2263.74),
            ('P.P', -501.6),
            ('ATN.CAR.2', 0),
            ('ATN.INT.2', 0),
            ('ATN.MOB.2', 0),
            ('M.ONSS', -34.72),
            ('MEAL_V_EMP', -22.89),
            ('REP.FEES', 150),
            ('IP', 913.83),
            ('IP.DED', -68.54),
            ('NET', 2699.83),
        ])

        employee = {
            'name': 'Roger2',
        }
        contract = {
            'name': 'Contract For Roger',
            'date_start': datetime.date(2018, 1, 1),
            'wage': 3746.33,
            'wage_on_signature': 3746.33,
            'meal_voucher_amount': 7.45,
            'representation_fees': 150,
            'internet': 0,
            'mobile': 0,
            'ip_wage_rate': 25,
            'ip': True,
            'resource_calendar_id': self.classic_38h_calendar.id,
        }
        payslip = {
            'date_from': datetime.date.today().replace(year=2018, month=11, day=1),
            'date_to': datetime.date.today().replace(year=2018, month=11, day=30),
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
        }
        holidays_values = [{
            'name': 'Unpaid Leave 4 hours',
            'holiday_status_id': self.leave_type_unpaid.id,
            'request_date_from': datetime.date(2018, 11, 6),
            'request_date_to': datetime.date(2018, 11, 6),
            'request_hour_from': '7',
            'request_hour_to': '12',
        }, {
            'name': 'Bank Holiday',
            'holiday_status_id': self.leave_type_bank_holidays.id,
            'request_date_from': datetime.date(2018, 11, 9),
            'request_date_to': datetime.date(2018, 11, 9),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }]
        self.case_test(values, employee, payslip_values=payslip, contract_values=contract, holidays_values=holidays_values)

    # 2 unpaid days + 2 bank holidays + IP + Mobile + 1 child + extra leaves
    # IP should be correct as we are in 2019,
    def test_with_car_with_atn_with_child(self):
        values = OrderedDict([
            ('BASIC', 3198.87),
            ('ATN.INT', 5.00),
            ('ATN.MOB', 0.0),
            ('SALARY', 3203.87),
            ('ONSS', -418.75),
            ('ATN.CAR', 109.92),
            ('GROSSIP', 2895.05),
            ('IP.PART', -799.72),
            ('GROSS', 2095.33),
            ('P.P', -343.31),
            ('ATN.CAR.2', -109.92),
            ('ATN.INT.2', -5.00),
            ('ATN.MOB.2', 0),
            ('M.ONSS', -29.7),
            ('MEAL_V_EMP', -20.71),
            ('REP.FEES', 150.0),
            ('IP', 799.72),
            ('IP.DED', -59.98),
            ('NET', 2476.43),
        ])
        address = self.env['res.partner'].create({
            'name': 'Roger',
        })
        employee = {
            'name': 'Roger3',
            'address_home_id': address.id,
            'marital': 'cohabitant',
            'spouse_fiscal_status': 'high_income',
            'children': 1,
        }
        model = self.env['fleet.vehicle.model'].create({
            'name': 'Opel Model',
            'brand_id': self.env.ref('fleet.brand_opel').id,
        })
        car = {
            'model_id': model.id,
            'driver_id': address.id,
            'acquisition_date': datetime.date(2018, 1, 15),
            'first_contract_date': datetime.date(2018, 1, 15),
            'car_value': 29235.15,
            'fuel_type': 'diesel',
            'co2': 89,
            'company_id': self.env.company.id,
        }
        car_contract = {
            'recurring_cost_amount_depreciated': 562.52,
        }
        contract = {
            'name': 'Contract For Roger The Fierce',
            'date_start': datetime.date(2019, 1, 1),
            'wage': 3542.63,
            'fuel_card': 150,
            'holidays': 1,
            'meal_voucher_amount': 7.45,
            'representation_fees': 150,
            'internet': 38,
            'mobile': 0,
            'ip_wage_rate': 25,
            'ip': True,
            'resource_calendar_id': self.classic_38h_calendar.id,
        }
        payslip = {
            'date_from': datetime.date.today().replace(year=2019, month=5, day=1),
            'date_to': datetime.date.today().replace(year=2019, month=5, day=31),
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
        }
        holiday = [{
            'name': 'Unpaid Leave Day 1',
            'holiday_status_id': self.leave_type_unpaid.id,
            'request_date_from': datetime.date(2019, 5, 1),
            'request_date_to': datetime.date(2019, 5, 1),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }, {
            'name': 'Unpaid Leave Day 2',
            'holiday_status_id': self.leave_type_unpaid.id,
            'request_date_from': datetime.date(2019, 5, 2),
            'request_date_to': datetime.date(2019, 5, 2),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }, {
            'name': 'Bank Holiday Day 1',
            'holiday_status_id': self.leave_type_bank_holidays.id,
            'request_date_from': datetime.date(2019, 5, 6),
            'request_date_to': datetime.date(2019, 5, 6),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }, {
            'name': 'Bank Holiday Day 2',
            'holiday_status_id': self.leave_type_bank_holidays.id,
            'request_date_from': datetime.date(2019, 5, 7),
            'request_date_to': datetime.date(2019, 5, 7),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }]
        self.case_test(values, employee, payslip_values=payslip, contract_values=contract, holidays_values=holiday, car_values=car, car_contract_values=car_contract)

    # ATN + No leave + IP (2019) + car
    def test_with_car_with_atn_with_car(self):
        values = OrderedDict([
            ('BASIC', 3452.4),
            ('ATN.INT', 5.00),
            ('ATN.MOB', 0.0),
            ('SALARY', 3457.4),
            ('ONSS', -451.88),
            ('ATN.CAR', 109.17),
            ('GROSSIP', 3114.68),
            ('IP.PART', -863.1),
            ('GROSS', 2251.58),
            ('P.P', -458.76),
            ('ATN.CAR.2', -109.17),
            ('ATN.INT.2', -5.00),
            ('ATN.MOB.2', 0),
            ('M.ONSS', -32.48),
            ('MEAL_V_EMP', -22.89),
            ('REP.FEES', 150.00),
            ('IP', 863.1),
            ('IP.DED', -64.73),
            ('NET', 2571.65),
        ])
        address = self.env['res.partner'].create({
            'name': 'Roger4',
        })
        employee = {
            'name': 'Roger4',
            'address_home_id': address.id,
            'marital': 'cohabitant',
            'spouse_fiscal_status': 'high_income',
        }
        model = self.env['fleet.vehicle.model'].create({
            'name': 'Opel Model',
            'brand_id': self.env.ref('fleet.brand_opel').id,
        })
        car = {
            'model_id': model.id,
            'driver_id': address.id,
            'acquisition_date': datetime.date(2014, 12, 10),
            'first_contract_date': datetime.date(2014, 12, 10),
            'car_value': 28138.86,
            'fuel_type': 'diesel',
            'co2': 88.00,
            'company_id': self.env.company.id,
        }
        car_contract = {
            'recurring_cost_amount_depreciated': 503.12,
        }
        contract = {
            'name': 'Contract For Roger',
            'date_start': datetime.date(2019, 1, 1),
            'wage': 3470.36,
            'wage_on_signature': 3470.36,
            'fuel_card': 150,
            'holidays': 1,
            'meal_voucher_amount': 7.45,
            'representation_fees': 150,
            'internet': 38,
            'mobile': 0,
            'ip_wage_rate': 25,
            'ip': True,
            'resource_calendar_id': self.classic_38h_calendar.id,
        }
        payslip = {
            'date_from': datetime.date.today().replace(year=2019, month=3, day=1),
            'date_to': datetime.date.today().replace(year=2019, month=3, day=31),
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
        }
        self.case_test(values, employee, payslip_values=payslip, contract_values=contract, car_values=car, car_contract_values=car_contract)

    # No IP, with employment bonus
    def test_no_ip_emp_bonus(self):
        values = OrderedDict([
            ('BASIC', 2075.44),
            ('SALARY', 2075.44),
            ('ONSS', -271.26),
            ('EmpBonus.1', 106.44),
            ('P.P', -299.68),
            ('M.ONSS', -9.88),
            ('MEAL_V_EMP', -21.8),
            ('P.P.DED', 35.27),
            ('NET', 1614.53),
        ])

        employee = {
            'name': 'Roger',
        }

        contract = {
            'name': 'Contract For Roger',
            'date_start': datetime.date(2015, 1, 1),
            'representation_fees': 0,
            'wage': 2075.44,
            'wage_on_signature': 2075.44,
            'internet': False,
            'mobile': False,
        }

        payslip = {
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
            'date_from': datetime.date(2019, 2, 1),
            'date_to': datetime.date(2019, 2, 28),
        }

        self.case_test(values, employee, payslip_values=payslip, contract_values=contract)

    # Small unemployment leave, spouse without income
    def test_small_unemployment_leave(self):
        values = OrderedDict([
            ('BASIC', 2706.14),
            ('ATN.INT', 5.0),
            ('ATN.MOB', 4.0),
            ('SALARY', 2715.14),
            ('ONSS', -354.87),
            ('P.P', -2.11),
            ('IP.DED', -50.74),
            ('M.ONSS', -24.28),
            ('MEAL_V_EMP', -19.62),
            ('ATN.INT.2', -5.0),
            ('ATN.MOB.2', -4.0),
            ('REP.FEES', 150.0),
            ('IP', 676.54),
            ('NET', 2404.53),
        ])

        employee = {
            'name': 'Roger',
            'resource_calendar_id': self.classic_38h_calendar.id,
            'marital': 'married',
            'children': 1,
            'spouse_fiscal_status': 'without_income',
        }
        car_vals = {
            'model_id': self.env.ref("fleet.model_a3").id,
            'license_plate': '1-JFC-095',
            'acquisition_date': time.strftime('%Y-01-01'),
            'co2': 88,
            'driver_id': self.env['res.partner'].create({'name': 'Roger'}).id,
            'car_value': 38000,
            'company_id': self.env.company.id,
        }
        contract = {
            'name': 'Contract For Roger',
            'date_start': datetime.date(2015, 1, 1),
            'wage': 2706.14,
            'wage_on_signature': 2706.14,
            'representation_fees': 150,
            'internet': True,
            'mobile': True,
            'ip': True,
            'ip_wage_rate': 25,
            'resource_calendar_id': self.classic_38h_calendar.id,
        }

        holidays_values = [{
            'name': 'Small Unemployment - Day 1',
            'holiday_status_id': self.leave_type_small_unemployment.id,
            'request_date_from': datetime.date(2019, 2, 27),
            'request_date_to': datetime.date(2019, 2, 27),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }, {
            'name': 'Small Unemployment - Day 2',
            'holiday_status_id': self.leave_type_small_unemployment.id,
            'request_date_from': datetime.date(2019, 2, 28),
            'request_date_to': datetime.date(2019, 2, 28),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }]

        payslip = {
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary'),
            'date_from': datetime.date(2019, 2, 1),
            'date_to': datetime.date(2019, 2, 28)
        }

        self.case_test(values, employee, payslip_values=payslip, contract_values=contract, holidays_values=holidays_values, car_values=car_vals)

    # PFI with company car
    def test_pfi_company_car_pay(self):
        values = OrderedDict([
            ('BASIC', 1653.11),
            ('SALARY', 1653.11),
            ('P.P', -360.48),        # 20% of BASIC + ATN.CAR
            ('ATN.CAR', 149.29),
            ('ATN.CAR.2', -149.29),
            ('MEAL_V_EMP', -23.98),
            ('NET', 1268.65),
        ])

        employee = {
            'name': 'Roger'
        }

        car_vals = {
            'model_id': self.env.ref("fleet.model_a3").id,
            'license_plate': '1-JFC-095',
            'acquisition_date': time.strftime('%Y-01-01'),
            'co2': 88,
            'car_value': 38000,
            'company_id': self.env.company.id,
        }

        contract = {
            'name': 'PFI Contract for Roger',
            'date_start': datetime.date(2015, 1, 1),
            'wage': 1653.11,
            'wage_on_signature': 1653.11,
            'meal_voucher_amount': 7.45,
            'internet': False,
            'mobile': False,
            'transport_mode_car': True,
        }

        holidays_values = [{
            'name': 'Bank Holiday',
            'holiday_status_id': self.leave_type_bank_holidays.id,
            'request_date_from': datetime.date(2019, 1, 1),
            'request_date_to': datetime.date(2019, 1, 1),
            'request_hour_from': '7',
            'request_hour_to': '18',
        }]

        payslip = {
            'date_from': datetime.date(2019, 1, 1),
            'date_to': datetime.date(2019, 1, 31),
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_pfi'),
        }

        self.case_test(values, employee, payslip_values=payslip, contract_values=contract, holidays_values=holidays_values, car_values=car_vals)

    # PFI with company car, mobile and internet
    def test_pfi_with_benefits_pay(self):
        values = OrderedDict([
            ('BASIC', 1572.8),
            ('ATN.INT', 5),
            ('ATN.MOB', 4),
            ('SALARY', 1581.8),
            ('P.P', -344.42),        # 20% of BASIC + ATN.CAR 
            ('ATN.CAR', 149.29),
            ('MEAL_V_EMP', -21.8),
            ('ATN.INT.2', -5),
            ('ATN.MOB.2', -4),
            ('ATN.CAR.2', -149.29),
            ('NET', 1206.58),
        ])

        employee = {
            'name': 'Roger'
        }
        car_vals = {
            'model_id': self.env.ref("fleet.model_a3").id,
            'license_plate': '1-JFC-095',
            'acquisition_date': time.strftime('%Y-01-01'),
            'co2': 88,
            'car_value': 38000,
            'company_id': self.env.company.id,
        }
        contract = {
            'name': 'PFI Contract for Roger',
            'date_start': datetime.date(2015, 1, 1),
            'wage': 1572.8,
            'wage_on_signature': 1572.8,
            'meal_voucher_amount': 7.45,
            'internet': True,
            'mobile': True,
            'transport_mode_car': True,
        }

        payslip = {
            'date_from': datetime.date(2019, 2, 1),
            'date_to': datetime.date(2019, 2, 28),
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_pfi'),
        }

        self.case_test(values, employee, payslip_values=payslip, contract_values=contract, car_values=car_vals)
