# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountBudget(TestAccountBudgetCommon):

    def test_account_budget(self):

        # Creating a crossovered.budget record
        budget = self.env['crossovered.budget'].create({
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'name': 'Budget 2019',
            'state': 'draft'
        })

        # I created two different budget lines
        # Modifying a crossovered.budget record
        self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': budget.id,
            'analytic_account_id': self.analytic_account_partner_b.id,
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'general_budget_id': self.account_budget_post_purchase0.id,
            'planned_amount': 10000.0,
        })
        self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': budget.id,
            'analytic_account_id': self.analytic_account_partner_a_2.id,
            'date_from': '2019-09-01',
            'date_to': '2019-09-30',
            'general_budget_id': self.account_budget_post_sales0.id,
            'planned_amount': 400000.0,
        })

        self.assertRecordValues(budget, [{'state': 'draft'}])

        # I pressed the confirm button to confirm the Budget
        # Performing an action confirm on module crossovered.budget
        budget.action_budget_confirm()

        # I check that budget is in "Confirmed" state
        self.assertRecordValues(budget, [{'state': 'confirm'}])

        # I pressed the validate button to validate the Budget
        # Performing an action validate on module crossovered.budget
        budget.action_budget_validate()

        # I check that budget is in "Validated" state
        self.assertRecordValues(budget, [{'state': 'validate'}])

        # I pressed the done button to set the Budget to "Done" state
        # Performing an action done on module crossovered.budget
        budget.action_budget_done()

        # I check that budget is in "done" state
        self.assertRecordValues(budget, [{'state': 'done'}])
