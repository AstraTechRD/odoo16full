# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class TestWebGridEmployee(models.Model):
    _name = 'test.web.grid.employee'
    _description = 'Test Web Grid Employee'

    name = fields.Char()


class TestWebGridProject(models.Model):
    _name = 'test.web.grid.project'
    _description = 'Test Web Grid Project'

    name = fields.Char()


class TestWebGridTask(models.Model):
    _name = 'test.web.grid.task'
    _description = 'Test Web Grid Task'

    name = fields.Char()
    project_id = fields.Many2one('test.web.grid.project')


class TestWebGrid(models.Model):
    _name = 'test.web.grid'
    _description = 'Test Web Grid'

    start_datetime = fields.Datetime()
    start_date = fields.Date()

    employee_id = fields.Many2one('test.web.grid.employee')
    project_id = fields.Many2one('test.web.grid.project')
    task_id = fields.Many2one('test.web.grid.task')
    partner_id = fields.Many2one('res.partner')

    resource_hours = fields.Float()
    validated = fields.Boolean("Validated", group_operator="bool_and", readonly=True)
