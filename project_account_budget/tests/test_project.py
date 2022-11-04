# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProject(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
            'company_id': False,
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Project - AA',
            'code': 'AA-1234',
            'plan_id': cls.analytic_plan.id,
        })
        cls.project_goats.write({'analytic_account_id': cls.analytic_account.id})

    def test_get_budget_items(self):
        if not self.project_pigs.analytic_account_id:
            self.assertEqual(self.project_pigs._get_budget_items(False), None, 'No budget should be return since no AA is set into the project.')
        self.assertTrue(self.env.user.has_group('analytic.group_analytic_accounting'))
        self.assertDictEqual(
            self.project_goats._get_budget_items(False),
            {
                'data': [],
                'total': {'allocated': 0, 'spent': 0},
                'can_add_budget': False,
            },
            'No budget has been created for this project.'
        )

        today = date.today()
        budget = self.env['crossovered.budget'].create({
            'name': 'Project Goats Budget',
            'crossovered_budget_line': [Command.create({
                'analytic_account_id': self.analytic_account.id,
                'date_from': today.replace(day=1),
                'date_to': today + relativedelta(months=1, days=-1),
                'planned_amount': 500,
            })],
        })
        budget.action_budget_confirm()

        budget_items = self.project_goats._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': 500.0, 'spent': 0.0},
            'can_add_budget': False,
        })
