# -*- coding: utf-8 -*-

import pytz

from .common import TestWebGrid
from odoo.fields import Datetime


class TestReadGridDomainDatetime(TestWebGrid):

    def test_read_grid_domain_datetime(self):

        field = "start_datetime"
        grid_anchor = '2019-06-14 00:00:00'

        lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
        lang.write({'week_start': '1'})

        domain_day = self.grid_obj_1.with_context(grid_anchor=grid_anchor).read_grid_domain(field, self.range_day)

        # For checking different span and step in week
        domain_week = self.grid_obj_1.with_context(grid_anchor=grid_anchor).read_grid_domain(field, self.range_week)
        domain_week_2 = self.grid_obj_1.with_context(grid_anchor=grid_anchor).read_grid_domain(field, self.range_week_2)

        domain_month = self.grid_obj_1.with_context(grid_anchor=grid_anchor).read_grid_domain(field, self.range_month)

        self.assertEqual(domain_day, ['&', ('start_datetime', '>=', '2019-06-01 00:00:00'), ('start_datetime', '<=', '2019-06-30 23:59:59')])
        self.assertEqual(domain_week, ['&', ('start_datetime', '>=', '2019-06-10 00:00:00'), ('start_datetime', '<=', '2019-06-16 23:59:59')])
        self.assertEqual(domain_week_2, ['&', ('start_datetime', '>=', '2019-05-27 00:00:00'), ('start_datetime', '<=', '2019-06-30 23:59:59')])
        self.assertEqual(domain_month, ['&', ('start_datetime', '>=', '2019-01-01 00:00:00'), ('start_datetime', '<=', '2019-12-31 23:59:59')])

        # For checking timezone conversion
        timezone = 'Asia/Kolkata'
        domain_day = self.grid_obj_1.with_context(tz=timezone, grid_anchor=grid_anchor).read_grid_domain(field, self.range_day)
        domain_week = self.grid_obj_1.with_context(tz=timezone, grid_anchor=grid_anchor).read_grid_domain(field, self.range_week)
        domain_month = self.grid_obj_1.with_context(tz=timezone, grid_anchor=grid_anchor).read_grid_domain(field, self.range_month)

        self.assertEqual(domain_day, ["&", ("start_datetime", ">=", "2019-05-31 18:30:00"), ("start_datetime", "<=", "2019-06-30 18:29:59")])
        self.assertEqual(domain_week, ['&', ('start_datetime', '>=', '2019-06-09 18:30:00'), ('start_datetime', '<=', '2019-06-16 18:29:59')])
        self.assertEqual(domain_month, ['&', ('start_datetime', '>=', '2018-12-31 18:30:00'), ('start_datetime', '<=', '2019-12-31 18:29:59')])

    def test_read_grid_method_datetime(self):
        project_id = self.grid_obj_1.project_id
        row_field = []
        col_field = "start_datetime"
        cell_field = "resource_hours"
        domain = [('project_id', '=', project_id.id)]

        lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
        lang.write({'week_start': '1'})

        timezone = 'Asia/Kolkata'
        # For checking for day range ('span': 'month', 'step': 'day')
        result_read_grid = self.grid_obj_1.with_context(tz=timezone, grid_anchor="2019-06-14 00:00:00").read_grid(row_field, col_field, cell_field, domain, self.range_day)

        # For checking today, previous and next grid_anchor
        self.assertEqual(result_read_grid.get('prev').get('grid_anchor'), "2019-05-14 00:00:00")
        self.assertEqual(result_read_grid.get('next').get('grid_anchor'), "2019-07-14 00:00:00")

        today_utc = pytz.utc.localize(Datetime.today(self.env.user))
        today_user_tz = today_utc.astimezone(pytz.timezone('Asia/Kolkata'))
        self.assertEqual(result_read_grid.get('initial').get('grid_anchor'), Datetime.to_string(today_user_tz))

        # Should have 30 cols for 30 days of June and 1 row for grid_obj_1
        self.assertEqual(len(result_read_grid.get('cols')), 30)
        self.assertEqual(len(result_read_grid.get('rows')), 1)

        day_of_work = self.grid_obj_1.start_datetime.day - 1
        self.assertEqual(result_read_grid.get('grid')[0][day_of_work].get('value'), self.grid_obj_1.resource_hours)

        # For checking readonly of freeze cell
        result_read_grid_readonly = self.grid_obj_1_validated.with_context(grid_anchor="2019-06-14 00:00:00").read_grid(row_field, col_field, cell_field, domain, self.range_day, readonly_field='validated')
        day_of_work = self.grid_obj_1_validated.start_datetime.day - 1
        self.assertEqual(result_read_grid_readonly.get('grid')[0][day_of_work].get('readonly'), True)

        # For checking week range ('span': 'month', 'step': 'week')
        result_read_grid = self.grid_obj_1.with_context(grid_anchor="2019-06-14 00:00:00").read_grid(row_field, col_field, cell_field, domain, self.range_week_2)

        # Should have 5 weeks in cols
        self.assertEqual(len(result_read_grid.get('cols')), 5)
        col0 = result_read_grid.get('cols')[0]
        week1_start_date0 = col0.get('values').get('start_datetime')
        self.assertEqual(week1_start_date0[0], "2019-05-27 00:00:00/2019-06-03 00:00:00")
        col4 = result_read_grid.get('cols')[4]
        week1_start_date4 = col4.get('values').get('start_datetime')
        self.assertEqual(week1_start_date4[0], "2019-06-24 00:00:00/2019-07-01 00:00:00")

        # Since the start datetime for obj_1 is 2019-06-14 11:30:00, so it is the third week according to its domain
        self.assertEqual(result_read_grid.get('grid')[0][2].get('value'), self.grid_obj_1.resource_hours)  # resource_hours for grid_obj_1 is 3.0
