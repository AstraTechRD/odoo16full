# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import tagged, TransactionCase

@tagged('post_install', '-at_install')
class TestWorksheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.worksheet_template = cls.env['worksheet.template'].create({
            'name': 'New worksheet',
            'color': 4,
            'res_model': 'project.task',
        })
        cls.fsm_project = cls.env['project.project'].create({
            'name': 'Field Service',
            'is_fsm': True,
        })
        cls.second_fsm_project = cls.env['project.project'].create({
            'name': 'Field Service',
            'is_fsm': True,
            'allow_worksheets': True,
            'worksheet_template_id': cls.worksheet_template.id,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Costumer A'})
        cls.task = cls.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': cls.fsm_project.id,
            'partner_id': cls.partner.id,
        })

    def test_project_worksheet_template_propagation(self):
        """
            1) Test project template propagation when changing task project
            2) Test project template propagation when creating new task
        """
        self.assertEqual(self.task.worksheet_template_id, self.fsm_project.worksheet_template_id)
        self.assertTrue(self.second_fsm_project.worksheet_template_id)
        self.assertNotEqual(self.task.worksheet_template_id, self.second_fsm_project.worksheet_template_id)

        self.task.write({
            'project_id': self.second_fsm_project.id,
        })

        self.assertEqual(self.task.worksheet_template_id, self.second_fsm_project.worksheet_template_id)
        secondTask = self.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': self.second_fsm_project.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(secondTask.worksheet_template_id, self.second_fsm_project.worksheet_template_id)
        self.assertTrue(secondTask.allow_worksheets)
