# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import utc

from odoo.tests import tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.resource.models.resource import sum_intervals


@tagged('-at_install', 'post_install')
class TestSmartSchedule(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.projectuser_resource, cls.projectmanager_resource = cls.env['resource.resource'].create([
            {
                'calendar_id': cls.project_pigs.resource_calendar_id.id,
                'company_id': cls.user_projectuser.company_id.id,
                'name': cls.user_projectuser.name,
                'user_id': cls.user_projectuser.id,
                'tz': cls.user_projectuser.tz,
            },
            {
                'calendar_id': cls.project_pigs.resource_calendar_id.id,
                'company_id': cls.user_projectmanager.company_id.id,
                'name': cls.user_projectmanager.name,
                'user_id': cls.user_projectmanager.id,
                'tz': cls.user_projectmanager.tz,
            },
        ])

        today = datetime.now() + relativedelta(months=3, hour=21, minute=59, second=59, microsecond=0)
        cls.last_date_view = today + relativedelta(day=31)
        cls.end_datetime = today + relativedelta(day=1)
        cls.begin_datetime = cls.end_datetime - relativedelta(days=1, hour=22, minute=0, second=0, microsecond=0)
        cls.last_date_view_str = cls.last_date_view.strftime('%Y-%m-%d %H:%M:%S')
        cls.begin_datetime_str = cls.begin_datetime.strftime('%Y-%m-%d %H:%M:%S')
        cls.end_datetime_str = cls.end_datetime.strftime('%Y-%m-%d %H:%M:%S')

    def _get_expected_planned_dates_per_task_id(self, tasks, planned_date_begin, planned_date_end):
        planned_dates_per_task_id = {}
        tasks_by_resource_calendar_dict = tasks._get_tasks_by_resource_calendar_dict()
        for (calendar, tasks) in tasks_by_resource_calendar_dict.items():
            date_start, date_stop = self.env['project.task']._calculate_planned_dates(planned_date_begin, planned_date_end, calendar=calendar)
            for task in tasks:
                planned_dates_per_task_id[task.id] = date_start, date_stop
        return planned_dates_per_task_id

    def test_basic(self):
        """ Test smart schedule in basic case (without task dependencies) """
        tasks = self.env['project.task'] \
            .with_context({'mail_create_nolog': True, 'default_project_id': self.project_pigs.id}) \
            .create([
                {
                    'name': 'task_planned_hours_low_priority',
                    'planned_hours': 5,
                },
                {
                    'name': 'task_planned_hours_high_priority',
                    'planned_hours': 14,
                    'priority': '1',
                },
                {
                    'name': 'task_no_planned_hours_with_uid',
                    'user_ids': [self.user_projectuser.id, self.user_projectmanager.id],
                },
                {
                    'name': 'task_no_planned_hours_without_uid',
                },
            ])
        task_planned_hours_low_priority, task_planned_hours_high_priority, task_no_planned_hours_with_uid, task_no_planned_hours_without_uid = tasks

        result = tasks \
            .with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })

        self.assertDictEqual(result, {}, 'task should not be discarded')
        # task_planned_hours_high_priority
        self.assertEqual(self.user_projectmanager, task_planned_hours_high_priority.user_ids, 'wrong user id')
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_planned_hours_high_priority.planned_date_begin, task_planned_hours_high_priority.planned_date_end),
            task_planned_hours_high_priority.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_planned_hours_high_priority.planned_hours}) on this task for the user set'
        )

        expected_planned_dates_per_task_id = self._get_expected_planned_dates_per_task_id(task_no_planned_hours_with_uid + task_no_planned_hours_without_uid, self.begin_datetime, self.end_datetime)

        # task_no_planned_hours_with_uid
        expected_planned_date_begin, expected_planned_date_end = expected_planned_dates_per_task_id[task_no_planned_hours_with_uid.id]
        self.assertEqual(expected_planned_date_begin, task_no_planned_hours_with_uid.planned_date_begin, 'wrong date begin')
        self.assertEqual(expected_planned_date_end, task_no_planned_hours_with_uid.planned_date_end, 'wrong date end')
        self.assertEqual(self.user_projectmanager, task_no_planned_hours_with_uid.user_ids, 'wrong user id')
        # task_no_planned_hours_without_uid
        expected_planned_date_begin, expected_planned_date_end = expected_planned_dates_per_task_id[task_no_planned_hours_without_uid.id]
        self.assertEqual(expected_planned_date_begin, task_no_planned_hours_without_uid.planned_date_begin, 'wrong date begin')
        self.assertEqual(expected_planned_date_end, task_no_planned_hours_without_uid.planned_date_end, 'wrong date end')
        self.assertEqual(self.user_projectmanager, task_no_planned_hours_without_uid.user_ids, 'wrong user id')
        # task_planned_hours_low_priority
        self.assertEqual(self.user_projectmanager, task_planned_hours_low_priority.user_ids, 'wrong user id')
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_planned_hours_low_priority.planned_date_begin, task_planned_hours_low_priority.planned_date_end),
            task_planned_hours_low_priority.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_planned_hours_low_priority.planned_hours} hours) on this task for the user set'
        )

    def test_no_user(self):
        """ Test if there are no uid, the tasks are planned with the enterprise schedule """
        tasks = self.env['project.task'].with_context({'mail_create_nolog': True, 'default_project_id': self.project_pigs.id}).create([
            {
                'name': 'task_planned_hours_without_uid',
                'planned_hours': 5,
            },
            {
                'name': 'task_planned_hours_6_days_work',
                'planned_hours': 45,
            },
            {
                'name': 'task_no_planned_hours_with_uid',
                'user_ids': self.user_projectuser.ids,
            },
        ])
        task_planned_hours_without_uid, task_planned_hours_6_days_work, task_no_planned_hours_with_uid = tasks

        result = tasks \
            .with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': None,
            })
        self.assertDictEqual(result, {}, 'No further action should be applied and warnings should be displayed. It means all tasks should be scheduled')

        self.assertFalse(task_no_planned_hours_with_uid.user_ids, "task_no_planned_hours_with_uid: no user should be assigned to that task.")
        expected_planned_date_begin, expected_planned_date_end = self._get_expected_planned_dates_per_task_id(task_no_planned_hours_with_uid, self.begin_datetime, self.end_datetime)[task_no_planned_hours_with_uid.id]
        self.assertEqual(expected_planned_date_begin, task_no_planned_hours_with_uid.planned_date_begin, "task_no_planned_hours_with_uid: wrong date begin")
        self.assertEqual(expected_planned_date_end, task_no_planned_hours_with_uid.planned_date_end, "task_no_planned_hours_with_uid: wrong date end")

        self.assertFalse(task_planned_hours_without_uid.user_ids, "task_planned_hours_without_uid: wrong user_ids")
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_planned_hours_without_uid.planned_date_begin, task_planned_hours_without_uid.planned_date_end),
            task_planned_hours_without_uid.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_planned_hours_without_uid.planned_hours}) on this task for the user set'
        )

        self.assertFalse(task_planned_hours_6_days_work.user_ids, "task_planned_hours_6_days_work: wrong user_ids")
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_planned_hours_6_days_work.planned_date_begin, task_planned_hours_6_days_work.planned_date_end),
            task_planned_hours_6_days_work.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_planned_hours_6_days_work.planned_hours}) on this task for the user set'
        )

    def test_discarded_tasks(self):
        """ Test with discarded tasks

            test if the wizard get the correct date to schedule the discarded tasks
            test if the discarded tasks are left untouched.
            test if tasks on another project are correctly involved in the scheduling
        """
        self.env['project.task'].with_context({'mail_create_nolog': True}).create([
            {
                'name': 'task_fill_month',
                'project_id': self.project_goats.id,
                'planned_date_begin': self.begin_datetime,
                'planned_date_end': self.last_date_view,
                'user_ids': self.user_projectmanager.ids,
            },
            {
                'name': 'task_fill_month_2',
                'project_id': self.project_goats.id,
                'planned_date_begin': self.begin_datetime + relativedelta(months=1),
                'planned_date_end': self.last_date_view + relativedelta(months=1),
                'user_ids': self.user_projectmanager.ids,
            },
        ])
        tasks = self.env['project.task'].with_context({'mail_create_nolog': True, 'default_project_id': self.project_pigs.id}).create([
            {
                'name': 'task_discarded_without_uid',
                'planned_hours': 14,
            },
            {
                'name': 'task_discarded_with_uid',
                'user_ids': self.user_projectuser.ids,
                'planned_hours': 4,
            },
        ])
        task_discarded_without_uid, task_discarded_with_uid = tasks

        result = tasks \
            .with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })

        self.assertTrue(result)
        action = result.get('action', {})
        self.assertTrue(action, 'An action should be returned to open a wizard for the tasks planned outside the period viewed in the gantt view.')
        wizard_model_name = action.get('res_model', '')
        self.assertEqual(wizard_model_name, 'project.task.confirm.schedule.wizard', 'The model set on the action to call should be the one of the wizard.')
        wizard = self.env[wizard_model_name].browse(action.get('res_id', False))
        self.assertEqual(len(wizard.line_ids), 2, 'the two tasks must be discarded')
        self.assertEqual(wizard.user_id, self.user_projectmanager, 'wrong user_ids in wizard')

        # discarded_with_uid
        self.assertEqual(task_discarded_with_uid.user_ids, self.user_projectuser, 'The users assigned to the task should stay the same set when the task is created.')
        self.assertFalse(task_discarded_with_uid.planned_date_begin, 'date_begin must be false in tasks')
        self.assertFalse(task_discarded_with_uid.planned_date_end, 'date_end must be false in tasks')
        # discarded_without_uid
        self.assertFalse(task_discarded_without_uid.user_ids, 'No user should be assigned to that task')
        self.assertFalse(task_discarded_without_uid.planned_date_begin, 'date_begin must be false in that task')
        self.assertFalse(task_discarded_without_uid.planned_date_end, 'date_end must be false in that task')
        # wizard discarded_without_uid
        line_without_uid, line_with_uid = wizard.line_ids
        self.assertEqual(line_without_uid.task_id, task_discarded_without_uid, "wrong task id in wizard line without uid")
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(line_without_uid.date_begin, line_without_uid.date_end),
            task_discarded_without_uid.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_discarded_without_uid.planned_hours}) on this task for the user set'
        )
        # wizard discarded_with_uid
        self.assertEqual(line_with_uid.task_id, task_discarded_with_uid, "wrong task id in wizard line with uid")
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(line_with_uid.date_begin, line_with_uid.date_end),
            task_discarded_with_uid.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_discarded_with_uid.planned_hours}) on this task for the user set'
        )

    def test_multiple_projects(self):
        """ test the behavior in case of tasks from multiple projects/ non fsm project are given. """
        tasks = self.env['project.task'].with_context({'mail_create_nolog': True}).create([
            {
                'name': 'task_goat',
                'project_id': self.project_goats.id,
                'user_ids': self.user_projectmanager.ids,
                'planned_hours': 23,
            }, {
                'name': 'task_pig',
                'project_id': self.project_pigs.id,
                'planned_hours': 42,
            },
        ])
        task_goat, task_pig = tasks
        result = tasks \
            .with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })
        self.assertFalse(result, "The dict should be empty since a simple write will be done instead of using the smart scheduling")
        expected_planned_dates_per_task_id = self._get_expected_planned_dates_per_task_id(tasks, self.begin_datetime, self.end_datetime)
        expected_planned_date_begin, expected_planned_date_end = expected_planned_dates_per_task_id[task_pig.id]
        self.assertEqual(expected_planned_date_begin, task_pig.planned_date_begin, "task pig : wrong planned_date_begin")
        self.assertEqual(expected_planned_date_end, task_pig.planned_date_end, "task pig : wrong planned_date_end")
        self.assertEqual(self.user_projectmanager, task_pig.user_ids, "task pig : wrong user_ids")
        expected_planned_date_begin, expected_planned_date_end = expected_planned_dates_per_task_id[task_goat.id]
        self.assertEqual(expected_planned_date_begin, task_goat.planned_date_begin, "task goat : wrong planned_date_begin")
        self.assertEqual(expected_planned_date_end, task_goat.planned_date_end, "task goat : wrong planned_date_end")
        self.assertEqual(self.user_projectmanager, task_goat.user_ids, "task goat : wrong user_ids")

    def test_small_tasks(self):
        """ test if the dates scheduled are the end or beginning of work intervals """
        tasks = self.env['project.task'] \
            .with_context({'mail_create_nolog': True, 'default_project_id': self.project_pigs.id}) \
            .create([
                {
                    'name': 'task_1',
                    'planned_hours': 1,
                },
                {
                    'name': 'task_two_days',
                    'planned_hours': 14,
                },
                {
                    'name': 'task_1_and_half_day',
                    'planned_hours': 10,
                },
            ])
        task_1, task_two_days, task_1_and_half_day = tasks

        result = tasks \
            .with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })
        self.assertDictEqual(result, {}, 'tasks should not be discarded')
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_1.planned_date_begin, task_1.planned_date_end),
            task_1.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_1.planned_hours}) on this task for the user set'
        )
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_two_days.planned_date_begin, task_two_days.planned_date_end),
            task_two_days.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_two_days.planned_hours}) on this task for the user set'
        )
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_1_and_half_day.planned_date_begin, task_1_and_half_day.planned_date_end),
            task_1_and_half_day.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_1_and_half_day.planned_hours}) on this task for the user set'
        )

    def test_long_task(self):
        """ test if task can be scheduled on long intervals (<1 month) """
        task_240_hours = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'tasks_200_hours',
            'project_id': self.project_pigs.id,
            'planned_hours': 240,
        })

        result = task_240_hours.with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })
        self.assertDictEqual(result, {}, "the tasks have to be scheduled")

        self.assertEqual(self.user_projectmanager, task_240_hours.user_ids, "wrong user id")
        work_intervals, dummy = self.user_projectmanager._get_valid_work_intervals(
            task_240_hours.planned_date_begin.replace(tzinfo=utc),
            task_240_hours.planned_date_end.replace(tzinfo=utc)
        )
        planned_hours_count = sum_intervals(work_intervals[self.user_projectmanager.id])
        self.assertEqual(
            planned_hours_count,
            task_240_hours.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_240_hours.planned_hours}) on this task for the user set'
        )

    def test_with_leaves(self):
        """ test if the personal leaves from an employee are correctly taken into account """
        simple_task = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'task_planned_hours_low_priority',
            'project_id': self.project_pigs.id,
            'planned_hours': 32,
        })
        begin_leave1 = self.end_datetime + relativedelta(days=2)
        begin_leave2 = end_leave1 = self.end_datetime + relativedelta(days=7)
        end_leave2 = self.end_datetime + relativedelta(days=14)

        self.env['resource.calendar.leaves'].with_context({'mail_create_nolog': True}).create([
            {
                'name': 'scheduled leave',
                'date_from': begin_leave1,
                'date_to': end_leave1,
                'resource_id': self.projectmanager_resource.id,
            },
            {
                'name': 'scheduled leave 2',
                'date_from': begin_leave2,
                'date_to': end_leave2,
                'resource_id': self.projectmanager_resource.id,
            },
        ])
        result = simple_task.with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })

        self.assertDictEqual(result, {}, "task must not be discarded")
        work_intervals, dummy = self.user_projectmanager._get_valid_work_intervals(
            simple_task.planned_date_begin.replace(tzinfo=utc),
            simple_task.planned_date_end.replace(tzinfo=utc)
        )
        planned_hours_count = sum_intervals(work_intervals[self.user_projectmanager.id])
        self.assertEqual(
            planned_hours_count,
            simple_task.planned_hours,
            f'The planned dates should be following the planned hours set (expected {simple_task.planned_hours}) on this task for the user set'
        )

    def test_with_dependencies(self):
        """ test if the task dependencies are correctly involved """
        task_already_planned, task_planned_hours = self.env['project.task'] \
            .with_context({'mail_create_nolog': True, 'default_project_id': self.project_pigs.id}) \
            .create([
                {
                    'name': 'task_already_planned',
                    'planned_date_begin': self.begin_datetime,
                    'planned_date_end': self.begin_datetime + relativedelta(days=5),
                    'user_ids': [self.user_projectuser.id],
                },
                {
                    'name': 'task_planned_hours',
                    'planned_hours': 5,
                },
            ])
        task_planned_hours.depend_on_ids |= task_already_planned

        result = task_planned_hours \
            .with_context({'last_date_view': self.last_date_view.strftime('%Y-%m-%d %H:%M:%S')}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'planned_date_end': self.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'user_ids': self.user_projectmanager.ids,
            })

        self.assertDictEqual(result, {}, 'task should not be discarded')
        self.assertEqual(
            self.project_pigs.resource_calendar_id.get_work_hours_count(task_planned_hours.planned_date_begin, task_planned_hours.planned_date_end),
            task_planned_hours.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_planned_hours.planned_hours}) on this task for the user set'
        )
        self.assertEqual(task_planned_hours.user_ids, self.user_projectmanager, 'wrong user id')

    def test_smart_schedule_with_task_dependencies(self):
        """ test if the recordset is correctly sorted when multiple dependencies are involved """
        tasks = self.env['project.task'] \
            .with_context({'mail_create_nolog': True, 'default_project_id': self.project_pigs.id})\
            .create([
                {
                    'name': 'Task 1',
                    'planned_hours': 5,
                },
                {
                    'name': 'Task 2',
                    'planned_hours': 6,
                    'priority': '1',
                },
                {
                    'name': 'Task 3',
                    'planned_hours': 3,
                },
            ])
        task_1, task_2, task_3 = tasks
        task_1.depend_on_ids = task_2 + task_3
        result = tasks \
            .with_context({'last_date_view': self.last_date_view_str}) \
            .schedule_tasks({
                'planned_date_begin': self.begin_datetime_str,
                'planned_date_end': self.end_datetime_str,
                'user_ids': self.user_projectmanager.ids,
            })
        self.assertDictEqual(result, {}, 'No tasks should be planned outside the gantt view and all tasks should be scheduled.')
        self.assertLess(task_3.planned_date_begin, task_1.planned_date_begin, 'The task 3 should be planned before the Task 1 since Task 3 blocks Task 1.')
        self.assertLess(task_2.planned_date_begin, task_1.planned_date_begin, 'The task 2 should be planned before the Task 1 since Task 3 blocks Task 1.')
        self.assertLess(task_2.planned_date_begin, task_3.planned_date_begin, 'The task 2 should be planned before the Task 3 since Task 2 has more priority than the Task 3.')

        # check if the planned dates follow the planned hours set on the three tasks
        # check for the Task 1
        work_intervals, dummy = self.user_projectmanager._get_valid_work_intervals(
            task_1.planned_date_begin.replace(tzinfo=utc),
            task_1.planned_date_end.replace(tzinfo=utc)
        )
        planned_hours_count = sum_intervals(work_intervals[self.user_projectmanager.id])
        self.assertEqual(
            planned_hours_count,
            task_1.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_1.planned_hours}) on this task for the user set'
        )
        work_intervals, dummy = self.user_projectmanager._get_valid_work_intervals(
            task_2.planned_date_begin.replace(tzinfo=utc),
            task_2.planned_date_end.replace(tzinfo=utc)
        )
        planned_hours_count = sum_intervals(work_intervals[self.user_projectmanager.id])
        self.assertEqual(
            planned_hours_count,
            task_2.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_2.planned_hours}) on this task for the user set'
        )
        work_intervals, dummy = self.user_projectmanager._get_valid_work_intervals(
            task_3.planned_date_begin.replace(tzinfo=utc),
            task_3.planned_date_end.replace(tzinfo=utc)
        )
        planned_hours_count = sum_intervals(work_intervals[self.user_projectmanager.id])
        self.assertEqual(
            planned_hours_count,
            task_3.planned_hours,
            f'The planned dates should be following the planned hours set (expected {task_3.planned_hours}) on this task for the user set'
        )
