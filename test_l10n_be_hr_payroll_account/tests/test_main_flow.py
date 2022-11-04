# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from contextlib import contextmanager

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Date, Datetime
from odoo.tests import common, Form, tagged
import time

@contextmanager
def additional_groups(user, groups):
    """ Quickly add groups to a user """
    group_ids = user.env["res.groups"]
    for xml_id in groups.split(','):
        group = user.env.ref(xml_id.strip(), raise_if_not_found=False)
        if group:
            group_ids |= group
    group_ids -= user.groups_id
    try:
        user.write({'groups_id': [(4, group.id, False) for group in group_ids]})
        yield user
    finally:
        user.write({'groups_id': [(3, group.id, False) for group in group_ids]})


@tagged('payroll_main_flow')
class TestHR(common.TransactionCase):

    def setUp(self):
        super(TestHR, self).setUp()
        self.user = self.create_user_employee(login='fgh', groups='sign.group_sign_user')
        self.user_leave_team_leader = self.create_user_employee(login='sef', groups='base.group_user')
        self.user.employee_id.leave_manager_id = self.user_leave_team_leader
        self.hr_user = self.create_user_employee(login='srt', groups='hr.group_hr_user')
        self.hr_holidays_user = self.create_user_employee(login='kut', groups='hr_holidays.group_hr_holidays_user')
        self.hr_holidays_manager = self.create_user_employee(login='bfd', groups='hr_holidays.group_hr_holidays_manager')

        self.hr_fleet_manager = self.create_user_employee(login='leh', groups='fleet.fleet_group_manager')

        self.hr_contract_manager = self.create_user_employee(login='nfz', groups='hr_contract.group_hr_contract_manager')
        self.hr_payroll_user = self.create_user_employee(login='ldj', groups='hr_payroll.group_hr_payroll_user,hr_holidays.group_hr_holidays_user')
        self.hr_payroll_manager = self.create_user_employee(login='lxt', groups='hr_payroll.group_hr_payroll_manager')

    def create_user_employee(self, login, groups):
        user = mail_new_test_user(self.env, login=login, groups=groups)
        user.company_id.country_id = self.env.ref('base.be')
        employee = self.env['hr.employee'].create({
            'name': 'Employee %s' % login,
            'user_id': user.id,
        })
        user.tz = employee.tz
        return user

    def create_leave_type(self, user, name='Leave Type', requires_allocation='no', employee_requests='yes', request_unit='day', validation='no_validation', allocation_validation='officer'):
        leave_type_form = Form(self.env['hr.leave.type'].with_user(user))
        leave_type_form.name = name
        leave_type_form.requires_allocation = requires_allocation
        # attrs="{'invisible': [('requires_allocation', '=', 'no')]}"
        if requires_allocation == 'yes':
            leave_type_form.employee_requests = employee_requests
            # attrs="{'invisible': ['|', ('requires_allocation', '=', 'no'), ('employee_requests', '=', 'no')]}"
            if employee_requests == 'yes':
                leave_type_form.allocation_validation_type = allocation_validation
        leave_type_form.leave_validation_type = validation
        leave_type_form.request_unit = request_unit
        leave_type_form.responsible_id = user
        return leave_type_form.save()

    def create_allocation(self, user, employee, leave_type, number_of_days=10):
        user.groups_id += self.env.ref('hr_holidays.group_hr_holidays_manager')
        allocation_form = Form(self.env['hr.leave.allocation'].with_user(user))
        # <field name="number_of_days" invisible="1"/>
        # @api.depends(...'number_of_days_display'...)
        # def _compute_from_holiday_status_id(self):
        #     ...
        #     for allocation in self:
        #         ...
        #         allocation.number_of_days = allocation.number_of_days_display
        #         ...
        allocation_form.number_of_days_display = number_of_days
        # <field name="employee_id" invisible="1" groups="hr_holidays.group_hr_holidays_user"/>
        # @api.depends('employee_ids')
        # def _compute_from_employee_ids(self):
        #     for allocation in self:
        #         if len(allocation.employee_ids) == 1:
        #             allocation.employee_id = allocation.employee_ids[0]._origin
        allocation_form.employee_ids.add(employee)
        allocation_form.name = 'New Request'
        allocation_form.date_from = time.strftime('2015-1-1')
        allocation_form.date_to = time.strftime('%Y-12-31')
        allocation_form.holiday_status_id = leave_type
        return allocation_form.save()

    def create_leave(self, user, leave_type, start, end, employee=None):
        employee = employee or user.employee_id
        leave_form = Form(self.env['hr.leave'].with_context(default_employee_id=employee.id).with_user(user))
        leave_form.holiday_status_id = leave_type
        leave_form.request_date_from = start
        leave_form.request_date_to = end
        return leave_form.save()

    def _test_leave(self):
        # --------------------------------------------------
        # Holiday manager: creates leave types
        # --------------------------------------------------
        self.leave_type_1 = self.create_leave_type(
            user=self.hr_holidays_manager,
            name='Leave Type (no allocation, validation HR, day)',
            request_unit='day',
            validation='hr',
        )
        self.leave_type_2 = self.create_leave_type(
            user=self.hr_holidays_manager,
            name='Leave Type (allocation by HR, no validation, half day)',
            requires_allocation='yes',
            employee_requests='no',
            allocation_validation='officer',
            request_unit='half_day',
            validation='no_validation',
        )
        self.leave_type_3 = self.create_leave_type(
            user=self.hr_holidays_manager,
            name='Leave Type (allocation request, validation both, hour)',
            requires_allocation='yes',
            employee_requests='yes',
            request_unit='hour',
            validation='both',
            allocation_validation='officer',
        )

        # --------------------------------------------------
        # Holiday user: Allocation
        # --------------------------------------------------
        allocation_no_validation = self.create_allocation(
            user=self.hr_holidays_user,
            employee=self.user.employee_id,
            leave_type=self.leave_type_2,
        )

        allocation_no_validation.action_confirm()

        # Holiday user refuse allocation
        allocation_no_validation.action_refuse()
        self.assertEqual(allocation_no_validation.state, 'refuse')

        # Holiday manager reset to draft
        allocation_no_validation.with_user(self.hr_holidays_manager).action_draft()
        self.assertEqual(allocation_no_validation.state, 'draft')

        # Holiday user approve allocation
        allocation_no_validation.action_confirm()
        allocation_no_validation.action_validate()
        self.assertEqual(allocation_no_validation.state, 'validate')
        self.assertEqual(allocation_no_validation.approver_id, self.hr_holidays_user.employee_id)

        # --------------------------------------------------
        # User: Allocation request
        # --------------------------------------------------

        # User request an allocation
        allocation = self.create_allocation(
            user=self.user,
            employee=self.user.employee_id,
            leave_type=self.leave_type_3,
        )
        self.assertEqual(allocation.state, 'draft')
        allocation.action_confirm()

        # Holiday Manager validates
        allocation.with_user(self.hr_holidays_manager).action_validate()
        self.assertEqual(allocation.state, 'validate')
        self.assertEqual(allocation.approver_id, self.hr_holidays_manager.employee_id)

        # --------------------------------------------------
        # User: Leave request
        # --------------------------------------------------

        # User request a leave which does not require validation
        leave_form = Form(self.env['hr.leave'].with_user(self.user))
        leave_form.holiday_status_id = allocation_no_validation.holiday_status_id
        leave_form.request_unit_half = True
        leave_form.request_date_from = Date.today() + relativedelta(days=1)
        leave_form.request_date_from_period = 'am'
        self.assertEqual(leave_form.number_of_days_display, 0.5, "Onchange should have computed 0.5 days")
        leave = leave_form.save()
        self.assertEqual(leave.state, 'validate', "Should be automatically validated")

        # User request a leave that doesn't require allocation
        leave = self.create_leave(
            user=self.user,
            leave_type=self.leave_type_1,
            start=Datetime.now() + relativedelta(days=2),
            end=Datetime.now() + relativedelta(days=3)
        )

        # User request a leave that require validation
        leave = self.create_leave(
            user=self.user,
            leave_type=allocation.holiday_status_id,
            start=Datetime.now() + relativedelta(days=6),
            end=Datetime.now() + relativedelta(days=8)
        )
        self.assertEqual(leave.state, 'confirm', "Should be in `confirm` state")

        # # Team leader approves
        leave.with_user(self.user_leave_team_leader).action_approve()
        self.assertEqual(leave.state, 'validate1')
        self.assertEqual(leave.first_approver_id, self.user_leave_team_leader.employee_id)

        # Holiday manager applies second approval
        # the "hr_holidays_manager" user need this group to access timesheets of other users
        with additional_groups(self.hr_holidays_manager, 'hr_timesheet.group_hr_timesheet_approver'):
            leave.with_user(self.hr_holidays_manager).action_validate()

        self.assertEqual(leave.state, 'validate')
        self.assertEqual(leave.second_approver_id, self.hr_holidays_manager.employee_id)

    def create_salary_structure_type(self, user):
        structure_type_form = Form(self.env['hr.payroll.structure.type'].with_user(user))
        structure_type_form.name = 'Structure Type - Test'
        return structure_type_form.save()

    def create_salary_structure(self, user, name, code):
        structure_type = self.create_salary_structure_type(user)

        struct_form = Form(self.env['hr.payroll.structure'].with_user(user))
        struct_form.name = name
        struct_form.type_id = structure_type
        return struct_form.save()

    def create_contract(self, user, name, structure, wage, employee, state, start, end=None, car=None):
        contract_form = Form(self.env['hr.contract'].with_user(user))
        contract_form.name = name
        contract_form.employee_id = employee
        contract_form.structure_type_id = structure.type_id
        contract_form.date_start = start
        contract_form.date_end = end
        if car:  # only for fleet manager
            # attrs="{'invisible': [('transport_mode_car', '=', False)]}"
            contract_form.transport_mode_car = True
            contract_form.car_id = car
        contract_form.wage = wage
        contract_form.state = state
        sign_template = self.env['sign.template'].search([], limit=1)
        contract_form.hr_responsible_id = self.user
        contract_form.sign_template_id = sign_template
        contract_form.contract_update_template_id = sign_template
        return contract_form.save()

    def create_work_entry_type(self, user, name, code, is_leave=False, leave_type=None):
        work_entry_type_form = Form(self.env['hr.work.entry.type'].with_user(user))
        work_entry_type_form.name = name
        work_entry_type_form.code = code
        return work_entry_type_form.save()

    def link_leave_work_entry_type(self, user, work_entry_type, leave_type):
        with Form(leave_type.with_user(user)) as leave_type_form:
            leave_type_form.work_entry_type_id = work_entry_type

    def create_vehicle_model(self, user, brand_name, model_name):
        vehicle_brand_form = Form(self.env['fleet.vehicle.model.brand'].with_user(user))
        vehicle_brand_form.name = brand_name
        brand = vehicle_brand_form.save()

        vehicle_model_form = Form(self.env['fleet.vehicle.model'].with_user(user))
        vehicle_model_form.name = model_name
        vehicle_model_form.brand_id = brand
        return vehicle_model_form.save()

    def create_vehicle(self, user, model, driver=None):
        vehicle_form = Form(self.env['fleet.vehicle'].with_user(user))
        vehicle_form.model_id = model
        vehicle_form.fuel_type = 'lpg'
        vehicle_form.driver_id = driver or self.env['res.partner']
        return vehicle_form.save()

    def create_structure(self, user, name, code):
        struct_form = Form(self.env['hr.payroll.structure'].with_user(user))
        struct_form.name = name
        struct_form.type_id = self.env.ref('hr_contract.structure_type_employee_cp200')
        return struct_form.save()

    def _test_contract(self):
        struct = self.create_salary_structure(self.hr_payroll_user, 'Salary Structure', 'SOO1')

        # Contract without car and without fleet access rights
        contract_cdd = self.create_contract(
            user=self.hr_contract_manager,
            name="%s's CDD" % self.user.employee_id,
            employee=self.user.employee_id,
            structure=struct,
            start=Date.today() + relativedelta(day=1, months=-1),
            end=Date.today().replace(day=15),
            wage=1500,
            state='close',
        )

        # Contract with a car and with access rights
        with additional_groups(self.hr_contract_manager, 'fleet.fleet_group_manager'):
            contract_cdi = self.create_contract(
                user=self.hr_contract_manager,
                name="%s's CDD" % self.user.employee_id,
                structure=struct,
                employee=self.user.employee_id,
                start=Date.today().replace(day=16),
                car=self.env['fleet.vehicle'].search([
                    ('driver_id', '=', self.user.employee_id.address_home_id.id),
                    ('company_id', '=', self.user.employee_id.company_id.id),
                ], limit=1),
                wage=2500,
                state='draft',
            )
            contract_cdi.state = 'open'

    def _test_work_entries(self):
        work_entry_type = self.create_work_entry_type(
            user=self.hr_payroll_manager,
            name='bla',
            code='TYPE100',
        )
        work_entry_type_leave = self.create_work_entry_type(
            user=self.hr_payroll_manager,
            name='bla bla',
            code='TYPE200',
            is_leave=True,
        )
        self.link_leave_work_entry_type(
            user=self.hr_holidays_manager,
            work_entry_type=work_entry_type_leave,
            leave_type=self.leave_type_1,
        )

        # Request a leave but don't approve it
        non_approved_leave = self.create_leave(
            user=self.user,
            leave_type=self.leave_type_1,
            start=Datetime.now() + relativedelta(days=12),
            end=Datetime.now() + relativedelta(days=13)
        )

        self.user.employee_id.with_user(self.hr_payroll_user).generate_work_entries(Datetime.today().replace(day=1), Datetime.today() + relativedelta(months=1, day=1, days=-1, hour=23, minute=59))
        work_entries = self.env['hr.work.entry'].with_user(self.hr_payroll_user).search([('employee_id', '=', self.user.employee_id.id)])
        # should not be able to validate
        self.assertFalse(work_entries.with_user(self.hr_payroll_user).action_validate())
        work_entries_with_error = work_entries.filtered(lambda b: b.state == 'conflict')

        self.env['hr.leave'].search([('employee_id', "=", self.user.employee_id.id)])
        # Check work_entries without a type
        undefined_type = work_entries_with_error.filtered(lambda b: not b.work_entry_type_id)
        self.assertTrue(undefined_type)  # some leave types we created earlier are not linked to any work entry type
        undefined_type.write({'work_entry_type_id': work_entry_type_leave.id})

        # Check work_entries conflicting with a leave, approve them as payroll manager
        conflicting_leave = work_entries_with_error.filtered(lambda b: b.leave_id and b.leave_id.state != 'validate')

        # this user need "group_hr_timesheet_approver" to access timesheets of other user
        # with additional_groups(self.hr_payroll_user, 'hr_timesheet.group_hr_timesheet_approver'):
        #     conflicting_leave.mapped('leave_id').with_user(self.hr_payroll_user).action_approve()

        # Reload work_entries (some might have been deleted/created when approving leaves)
        work_entries = self.env['hr.work.entry'].with_user(self.hr_payroll_user).search([('employee_id', '=', self.user.employee_id.id)])

        # Some work entries are still conflicting (if not completely included in a leave)
        self.assertFalse(work_entries.with_user(self.hr_payroll_user).action_validate())
        work_entries.filtered(lambda w: w.state == 'conflict').write({'state': 'cancelled'})
        self.assertTrue(work_entries.with_user(self.hr_payroll_user).action_validate())

    def _test_fleet(self):
        car_model = self.create_vehicle_model(
            user=self.hr_fleet_manager,
            brand_name="Cool Italian sport car manufacturer",
            model_name="Velociraptor",
        )

        car = self.create_vehicle(
            user=self.hr_fleet_manager,
            model=car_model,
        )

        # Add access rigths to be able to access the employee's private address
        # (in real use, the HR managing employees cars would be granted hr and fleet rights)
        with additional_groups(self.hr_fleet_manager, 'base.group_private_addresses'):
            with Form(car.with_user(self.hr_fleet_manager)) as car_form:
                car_form.driver_id = self.env['res.partner'].search([('id', '=', self.user.employee_id.address_home_id.id)], limit=1)

    def _test_payroll(self):
        struct = self.create_structure(
            user=self.hr_payroll_manager,
            name="Structure",
            code="STR100",
        )
        # TODO test payslip computation

    @patch.object(Date, 'today', lambda: date(2018, 10, 10))
    @patch.object(Datetime, 'today', lambda: datetime(2018, 10, 10, 0, 0, 0))
    @patch.object(Datetime, 'now', lambda: datetime(2018, 10, 10, 9, 18))
    def test_flow(self):
        self._test_fleet()
        self._test_contract()
        self._test_leave()
        self._test_work_entries()
        self._test_payroll()
