# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestPlanningOverlap(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tomorrow = datetime.now() + relativedelta(days=1)
        cls.task_1.write({
            'planned_date_begin': cls.tomorrow + relativedelta(hour=8),
            'planned_date_end': cls.tomorrow + relativedelta(hour=10),
        })

    def test_same_user_no_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(days=+1, hour=8),
            'planned_date_end': self.tomorrow + relativedelta(days=+1, hour=10),
        })

        tasks = self.task_1 + self.task_2
        overlaps = tasks._get_planning_overlap_per_task()
        self.assertFalse(overlaps.get(self.task_1.id))
        self.assertFalse(overlaps.get(self.task_2.id))

        search_result = self.env['project.task'].search([('planning_overlap', '=', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_different_users_overlap(self):
        self.task_2.write({
            'planned_date_begin': self.tomorrow + relativedelta(hour=9),
            'planned_date_end': self.tomorrow + relativedelta(hour=11),
        })

        tasks = self.task_1 + self.task_2
        overlaps = tasks._get_planning_overlap_per_task()
        self.assertFalse(overlaps.get(self.task_1.id))
        self.assertFalse(overlaps.get(self.task_2.id))

        search_result = self.env['project.task'].search([('planning_overlap', '=', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(hour=9),
            'planned_date_end': self.tomorrow + relativedelta(hour=11),
        })

        tasks = self.task_1 + self.task_2
        overlaps = tasks._get_planning_overlap_per_task()
        self.assertIn(self.task_1.id, overlaps)
        self.assertIn(self.task_2.id, overlaps)

        search_result = self.env['project.task'].search([('planning_overlap', '>', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_past_overlap(self):
        tasks = self.task_1 + self.task_2
        tasks.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(days=-5, hour=9),
            'planned_date_end': self.tomorrow + relativedelta(days=-5, hour=11),
        })

        overlaps = tasks._get_planning_overlap_per_task()
        self.assertFalse(overlaps.get(self.task_1.id))
        self.assertFalse(overlaps.get(self.task_2.id))

        search_result = self.env['project.task'].search([('planning_overlap', '=', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_done_overlap(self):
        stage_done = self.env['project.task.type'].create({
            'name': 'Stage Done',
            'fold': True,
        })
        self.project_pigs.type_ids = stage_done
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(hour=9),
            'planned_date_end': self.tomorrow + relativedelta(hour=11),
            'stage_id': stage_done.id,
        })

        tasks = self.task_1 + self.task_2
        overlaps = tasks._get_planning_overlap_per_task()
        self.assertFalse(overlaps.get(self.task_1.id))
        self.assertFalse(overlaps.get(self.task_2.id))

        search_result = self.env['project.task'].search([('planning_overlap', '=', 0)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)
