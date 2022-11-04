# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import odoo.tests

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, Command
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase


@odoo.tests.tagged('post_install', '-at_install')
class TestHrPayrollAccountCommon(TestPayslipContractBase):

    @classmethod
    def setUpClass(cls):
        super(TestHrPayrollAccountCommon, cls).setUpClass()

        cls.private_address = cls.env['res.partner'].create({'name': 'A private address'})
        cls.work_address = cls.env['res.partner'].create({'name': 'A work address'})

        cls.hr_employee_john = cls.env['hr.employee'].create({
            'address_home_id': cls.private_address.id,
            'address_id': cls.work_address.id,
            'birthday': '1984-05-01',
            'children': 0.0,
            'country_id': cls.env.ref('base.in').id,
            # 'department_id': cls.ref('hr.dep_rd'),
            'gender': 'male',
            'marital': 'single',
            'name': 'John',
        })

        cls.hr_employee_mark = cls.env['hr.employee'].create({
            'address_home_id': cls.private_address.id,
            'address_id': cls.work_address.id,
            'birthday': '1984-05-01',
            'children': 0.0,
            'country_id': cls.env.ref('base.in').id,
            # 'department_id': cls.ref('hr.dep_rd'),
            'gender': 'male',
            'marital': 'single',
            'name': 'Mark',
        })

        cls.account_journal = cls.env['account.journal'].create({
            'name' : 'MISC',
            'code' : 'MSC',
            'type' : 'general',
        })

        cls.hr_structure_softwaredeveloper = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'rule_ids': [
                (0, 0, {
                    'name': 'Professional Tax',
                    'amount_select': 'fix',
                    'sequence': 150,
                    'amount_fix': -200,
                    'code': 'PT',
                    'category_id': cls.env.ref('hr_payroll.DED').id,
                }), (0, 0, {
                    'name': 'Provident Fund',
                    'amount_select': 'percentage',
                    'sequence': 120,
                    'amount_percentage': -12.5,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'PF',
                    'category_id': cls.env.ref('hr_payroll.DED').id,
                }), (0, 0, {
                    'name': 'Meal Voucher',
                    'amount_select': 'fix',
                    'amount_fix': 10,
                    'quantity': 'worked_days.WORK100 and worked_days.WORK100.number_of_days',
                    'code': 'MA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 16,
                }), (0, 0, {
                    'name': 'Conveyance Allowance',
                    'amount_select': 'fix',
                    'amount_fix': 800,
                    'code': 'CA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 10,
                }), (0, 0, {
                    'name': 'House Rent Allowance',
                    'amount_select': 'percentage',
                    'amount_percentage': 40,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'HRA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 5,
                })
            ],
            'type_id': cls.env['hr.payroll.structure.type'].create({'name': 'Employee', 'country_id': False}).id,
        })

        cls.hr_structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Salary Structure Type',
            'struct_ids': [(4, cls.hr_structure_softwaredeveloper.id)],
            'default_struct_id': cls.hr_structure_softwaredeveloper.id,
        })

        cls.hr_contract_john = cls.env['hr.contract'].create({
            'date_end': fields.Date.to_string(datetime.now() + timedelta(days=365)),
            'date_start': date(2010, 1, 1),
            'name': 'Contract for John',
            'wage': 5000.0,
            'employee_id': cls.hr_employee_john.id,
            'structure_type_id': cls.hr_structure_type.id,
            'state': 'open',
        })

        cls.hr_payslip_john = cls.env['hr.payslip'].create({
            'employee_id': cls.hr_employee_john.id,
            'struct_id' : cls.hr_structure_softwaredeveloper.id,
            'contract_id': cls.hr_contract_john.id,
            'journal_id': cls.account_journal.id,
            'name': 'Test Payslip John',
            'number': 'PAYSLIPTEST01',
        })

        cls.hr_contract_mark = cls.env['hr.contract'].create({
            'date_end': fields.Date.to_string(datetime.now() + timedelta(days=365)),
            'date_start': date(2010, 1, 1),
            'name': 'Contract for Mark',
            'wage': 5000.0,
            'employee_id': cls.hr_employee_mark.id,
            'structure_type_id': cls.hr_structure_type.id,
            'state': 'open',
        })

        cls.hr_payslip_john.date_from = time.strftime('%Y-%m-01')
        # YTI Clean that brol
        cls.hr_payslip_john.date_to = str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10]

        cls.payslip_run = cls.env['hr.payslip.run'].create({
            'date_start': time.strftime('%Y-%m-01'),
            'date_end': str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10],
            'name': 'Payslip for Employee'
        })


@odoo.tests.tagged('post_install', '-at_install')
class TestHrPayrollAccount(TestHrPayrollAccountCommon):

    def test_00_hr_payslip_run(self):
        """ Checking the process of payslip run when you create payslip(s) in a payslip run and you validate the payslip run. """

        # I verify the payslip run is in draft state.
        self.assertEqual(self.payslip_run.state, 'draft', 'State not changed!')

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm the payslip run.
        self.payslip_run.action_validate()

        # I verify the payslips is in done state.
        for slip in self.payslip_run.slip_ids:
            self.assertEqual(slip.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created.
        for slip in self.payslip_run.slip_ids:
            self.assertTrue(slip.move_id, 'Accounting Entries has not been created!')

    def test_01_hr_payslip_run(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you validate the payslip(s). """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm all payslip(s) in the payslip run.
        self.payslip_run.slip_ids.action_payslip_done()

        # I verify the payslip(s) is in done state.
        for slip in self.payslip_run.slip_ids:
            self.assertEqual(slip.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created.
        for slip in self.payslip_run.slip_ids:
            self.assertTrue(slip.move_id, 'Accounting Entries has not been created!')

    def test_02_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you cancel the payslip(s). """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm all payslip(s) in the payslip run.
        self.payslip_run.slip_ids.action_payslip_cancel()

        # I verify the payslip(s) is in cancel state.
        for slip in self.payslip_run.slip_ids:
            self.assertEqual(slip.state, 'cancel', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are not created.
        for slip in self.payslip_run.slip_ids:
            self.assertFalse(slip.move_id, 'Accounting Entries has been created!')

    def test_03_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you cancel a payslip and confirm another. """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # Test only with payslip that were just generated. Remove the payslip from setup
        self.payslip_run.write({'slip_ids': [(3, self.hr_payslip_john.id)]})

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I cancel one payslip and confirm another in the payslip run.
        payslip_1 = self.payslip_run.slip_ids[0]
        payslip_2 = self.payslip_run.slip_ids[1]
        payslip_1.action_payslip_cancel()
        payslip_2.action_payslip_done()

        # I verify the payslips' states.
        self.assertEqual(payslip_1.state, 'cancel', 'State not changed!')
        self.assertEqual(payslip_2.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created or not.
        self.assertFalse(payslip_1.move_id, 'Accounting Entries has been created!')
        self.assertTrue(payslip_2.move_id, 'Accounting Entries has not been created!')

    def test_04_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you cancel a payslip and after you confirm the payslip run. """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # Storing the references to slip_ids[0] and slip_ids[1]
        # for later use, because the order of the One2many is not guaranteed
        slip0 = self.payslip_run.slip_ids[0]
        slip1 = self.payslip_run.slip_ids[1]

        # I cancel one payslip and after i confirm the payslip run.
        slip0.action_payslip_cancel()
        self.payslip_run.action_validate()

        # I verify the payslips' states.
        self.assertEqual(slip0.state, 'cancel', 'State not changed!')
        self.assertEqual(slip1.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created or not.
        self.assertFalse(slip0.move_id, 'Accounting Entries has been created!')
        self.assertTrue(slip1.move_id, 'Accounting Entries has not been created!')

    def test_05_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip run from a payslip and you validate it. """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I create and i add the payslip run to the payslip.
        self.hr_payslip_john.payslip_run_id = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.hr_payslip_john.payslip_run_id.state, 'close', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

    def test_06_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip run from a payslip and you validate the payslip run.  """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I create and i add the payslip run to the payslip.
        self.hr_payslip_john.payslip_run_id = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })
        self.hr_payslip_john.compute_sheet()

        # I validate the payslip run.
        self.hr_payslip_john.payslip_run_id.action_validate()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.hr_payslip_john.payslip_run_id.state, 'close', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

    def test_07_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip run from a payslip and you cancel it.  """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I create and i add the payslip run to the payslip.
        self.hr_payslip_john.payslip_run_id = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I cancel the payslip.
        self.hr_payslip_john.action_payslip_cancel()

        # I verify the payslip is in cancel state.
        self.assertEqual(self.hr_payslip_john.state, 'cancel', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.hr_payslip_john.payslip_run_id.state, 'close', 'State not changed!')

        # I verify that the Accounting Entry is not created.
        self.assertFalse(self.hr_payslip_john.move_id, 'Accounting entry has been created!')

    def test_08_hr_payslip(self):
        """ Checking the process of a payslip when you validate it and it has not a payslip run.  """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

    def test_09_hr_payslip(self):
        """Checking if taxes are added on a payslip accounting entry when there is a default tax on the journal"""

        # Create a default tax for the account on the salary rule.
        tax_account = self.env['account.account'].create({
            'name': 'Rental Tax',
            'code': '777777',
            'account_type': 'asset_current',
        })
        hra_tax = self.env['account.tax'].create({
            'name': "hra_tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'account_id': tax_account.id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'account_id': tax_account.id}),
            ],
        })

        # Create a account for the HRA salary rule.
        self.hra_account = self.env['account.account'].create({
            'name': 'House Rental',
            'code': '654321',
            'account_type': 'income',
            'tax_ids': [(4, hra_tax.id)]
        })

        # Assign the account to the salary rule and the rule to the hr structure.
        self.hra_rule.account_credit = self.hra_account
        self.hra_rule.account_debit = self.hra_account
        self.hr_structure_softwaredeveloper.rule_ids = [(4, self.hra_rule.id)]

        self.hr_payslip_john.compute_sheet()

        # Validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # Verify that the taxes are applied on hra move lines.
        for line in self.hr_payslip_john.move_id.line_ids:
            if line.account_id.id == self.hra_account.id:
                self.assertEqual(line.tax_ids, hra_tax, 'The account default tax is not added to move lines!')
