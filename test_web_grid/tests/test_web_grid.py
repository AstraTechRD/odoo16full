# -*- coding: utf-8 -*-

from .common import TestWebGrid
from odoo.fields import Date


class TestReadGridGrouped(TestWebGrid):

    def test_result(self):
        TestWebGrid = self.env['test.web.grid'].with_context(grid_anchor="2019-06-14")

        row_fields = ["task_id"]
        col_field = "start_date"
        cell_field = "resource_hours"
        section_field = "project_id"
        domain = []

        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        lang.week_start = '1'

        # A call to read_grid_grouped with grid_anchor should return data from 2019-06-01 to 2019-06-30
        result = TestWebGrid.read_grid_grouped(
            row_fields, col_field, cell_field, section_field, domain, self.range_day,
        )
        first_group = result[0]

        # Label for Many2one section_field is a tuple (id, name_get)
        project = self.grid_obj_2.project_id
        self.assertEqual(first_group['__label'], (project.id, project.display_name))

        # For checking today, previous and next grid_anchor
        today = Date.context_today(self.env.user)
        self.assertEqual(first_group['prev']['grid_anchor'], "2019-05-14")
        self.assertEqual(first_group['next']['grid_anchor'], "2019-07-14")
        self.assertEqual(first_group['initial']['grid_anchor'], Date.to_string(today))

        # Should have 7 cols for 7 days of June and 1 row for grid_obj_2
        self.assertEqual(len(first_group['cols']), 30)
        self.assertEqual(len(first_group['rows']), 1)

        date_of_work = self.grid_obj_2.start_date.day - 1
        self.assertEqual(first_group['grid'][0][date_of_work]['value'], self.grid_obj_2.resource_hours)

        # For checking readonly of freeze cell
        result = TestWebGrid.read_grid_grouped(
            row_fields, col_field, cell_field, section_field, domain, self.range_day,
            readonly_field='validated',
        )
        first_group = result[0]

        date_of_work = self.grid_obj_2_validated.start_date.day - 1
        self.assertEqual(first_group['grid'][0][date_of_work]['readonly'], True)

        # For checking week range ('span': 'month', 'step': 'week')
        result = TestWebGrid.read_grid_grouped(
            row_fields, col_field, cell_field, section_field, domain, self.range_week_2,
        )
        first_group = result[0]

        # Should have 5 weeks in cols
        self.assertEqual(len(first_group['cols']), 5)
        col0 = first_group['cols'][0]
        self.assertEqual(col0['values']['start_date'][0], "2019-05-27/2019-06-03")
        col4 = first_group['cols'][4]
        self.assertEqual(col4['values']['start_date'][0], "2019-06-24/2019-07-01")

        # Since the start_date for obj_2 is 2019-06-04, so it is the second week according to its domain
        self.assertEqual(first_group['grid'][0][1]['value'], self.grid_obj_2.resource_hours)  # resource_hours for grid_obj_2 is 4.0

    def test_performance(self):
        TestWebGrid = self.env['test.web.grid'].with_context(grid_anchor="2019-06-14")

        row_fields = ["task_id"]
        col_field = "start_date"
        cell_field = "resource_hours"
        section_field = "project_id"
        domain = []
        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        lang.week_start = '1'

        # warmup caches
        TestWebGrid.read_grid_grouped(
            row_fields, col_field, cell_field, section_field, domain, self.range_day,
        )

        # determine the number of queries with the initial data
        self.env.flush_all()
        self.env.invalidate_all()
        query_count = -self.cr.sql_log_count
        result = TestWebGrid.read_grid_grouped(
            row_fields, col_field, cell_field, section_field, domain, self.range_day,
        )
        self.env.flush_all()
        query_count += self.cr.sql_log_count
        base_size = len(result)

        # add records to generate more sections
        indexes = range(2, 10)
        projects = self.env['test.web.grid.project'].create([
            {'name': f'DragonballZ {index}'} for index in indexes
        ])
        tasks = self.env['test.web.grid.task'].create([
            {'name': f'Kill Freeza {index}', 'project_id': project.id}
            for index, project in zip(indexes, projects)
        ])
        self.env['test.web.grid'].create([
            {
                'employee_id': self.employee.id,
                'project_id': task.project_id.id,
                'task_id': task.id,
                'resource_hours': 3,
                'start_date': "2019-06-14",
            }
            for task in tasks
        ])

        # check that the query count has not increased
        with self.assertQueryCount(query_count):
            self.env.invalidate_all()
            result = TestWebGrid.read_grid_grouped(
                row_fields, col_field, cell_field, section_field, domain, self.range_day,
            )

        # There should be as many items in result than the number of different
        # projects linked to a test.web.grid that verifies the domain
        self.assertGreater(len(result), base_size)
        self.assertEqual(
            len(result),
            len(TestWebGrid.read_group(
                TestWebGrid.read_grid_domain(col_field, self.range_day),
                ['project_id'], ['project_id'],
            )),
        )
