# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import users

from .common import TestIndustryFsmCommon

@tagged('post_install', '-at_install')
class TestFsmFlow(TestIndustryFsmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'project 2',
            'privacy_visibility': 'followers',
        })

    def test_stop_timers_on_mark_as_done(self):
        self.assertEqual(len(self.task.sudo().timesheet_ids), 0, 'There is no timesheet associated to the task')
        timesheet = self.env['account.analytic.line'].with_user(self.marcel_user).create({'name': '', 'project_id': self.fsm_project.id})
        timesheet.action_add_time_to_timer(3)
        timesheet.action_change_project_task(self.fsm_project.id, self.task.id)
        self.assertTrue(timesheet.user_timer_id, 'A timer is linked to the timesheet')
        self.assertTrue(timesheet.user_timer_id.is_timer_running, 'The timer linked to the timesheet is running')
        task_with_henri_user = self.task.with_user(self.henri_user)
        task_with_henri_user.action_timer_start()
        self.assertTrue(task_with_henri_user.user_timer_id, 'A timer is linked to the task')
        self.assertTrue(task_with_henri_user.user_timer_id.is_timer_running, 'The timer linked to the task is running')
        task_with_george_user = self.task.with_user(self.george_user)
        result = task_with_george_user.action_fsm_validate()
        self.assertEqual(result['type'], 'ir.actions.act_window', 'As there are still timers to stop, an action is returned')
        Timer = self.env['timer.timer']
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', '=', self.task.id)])
        timesheets_running_timer_ids = Timer.search([('res_model', '=', 'account.analytic.line'), ('res_id', '=', timesheet.id)])
        self.assertEqual(len(timesheets_running_timer_ids), 1, 'There is still a timer linked to the timesheet')
        self.task.invalidate_model(['timesheet_ids'])
        self.assertEqual(len(tasks_running_timer_ids), 1, 'There is still a timer linked to the task')
        wizard = self.env['project.task.stop.timers.wizard'].create({'line_ids': [Command.create({'task_id': self.task.id})]})
        wizard.action_confirm()
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', '=', self.task.id)])
        timesheets_running_timer_ids = Timer.search([('res_model', '=', 'account.analytic.line'), ('res_id', '=', timesheet.id)])
        self.assertFalse(timesheets_running_timer_ids, 'There is no more timer linked to the timesheet')
        self.task.invalidate_model(['timesheet_ids'])
        self.assertFalse(tasks_running_timer_ids, 'There is no more timer linked to the task')
        self.assertEqual(len(self.task.sudo().timesheet_ids), 2, 'There are two timesheets')

    def test_mark_task_done_stage_assignment(self):
        self.assertFalse(self.fsm_project.type_ids)
        fold = [False, True, True, True]
        sequences = [5, 10, 40, 50]
        stage_1, stage_2, stage_3, stage_4 = self.env['project.task.type'].create([{
            'name': f'stage {i+1}',
            'fold': fold[i],
            'sequence': sequences[i],
            'project_ids': self.fsm_project.ids,
        } for i in range(len(fold))])
        self.assertTrue(self.fsm_project.type_ids)

        (self.task + self.second_task).write({
            'stage_id': stage_1.id,
        })
        self.task.action_fsm_validate()
        self.assertEqual(self.task.stage_id, stage_2, 'task is in stage 2 which is fold and with the lowest sequence of fold stages')

        (stage_2 + stage_3 + stage_4).fold = False

        second_task = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner.id,
            'stage_id': stage_1.id,
        })

        second_task.action_fsm_validate()
        self.assertEqual(second_task.stage_id, stage_4, "second_task is in stage 4 as there isn't any fold stages in second_task's project stages and as stage_4 has the highest sequence number.")

    @users('Project user', 'Project admin', 'Base user')
    def test_base_user_no_create_stop_timers_wizard(self):
        with self.assertRaises(AccessError):
            self.env['project.task.stop.timers.wizard'].with_user(self.env.user).create({'line_ids': [Command.create({'task_id': self.task.id})]})

    @users('Fsm user')
    def test_fsm_user_can_create_stop_timers_wizard(self):
        self.env['project.task.stop.timers.wizard'].with_user(self.env.user).create({'line_ids': [Command.create({'task_id': self.task.id})]})
