# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import json

from odoo import api, fields, models, _, _lt
from odoo.osv import expression


class Project(models.Model):
    _inherit = 'project.project'

    allow_forecast = fields.Boolean("Planning", default=True)
    total_forecast_time = fields.Integer(compute='_compute_total_forecast_time',
                                         help="Total number of forecast hours in the project rounded to the unit.", compute_sudo=True)

    def _compute_total_forecast_time(self):
        shifts_read_group = self.env['planning.slot']._read_group(
            [('start_datetime', '!=', False), ('end_datetime', '!=', False), ('project_id', 'in', self.ids)],
            ['project_id', 'allocated_hours'],
            ['project_id'],
        )
        shifts_per_project = {res['project_id'][0]: int(round(res['allocated_hours'])) for res in shifts_read_group}
        for project in self:
            project.total_forecast_time = shifts_per_project.get(project.id, 0)

    @api.depends('is_fsm')
    def _compute_allow_forecast(self):
        for project in self:
            if not project._origin:
                project.allow_forecast = not project.is_fsm

    def action_project_forecast_from_project(self):
        action = self.env["ir.actions.actions"]._for_xml_id("project_forecast.project_forecast_action_from_project")
        first_slot = self.env['planning.slot'].search([('start_datetime', '>=', datetime.datetime.now()), ('project_id', '=', self.id)], limit=1, order="start_datetime")
        action['context'] = {
            'default_project_id': self.id,
            'search_default_project_id': [self.id],
            **ast.literal_eval(action['context'])
        }
        action['display_name'] = _("%s's Planning", self.name)
        if first_slot:
            action['context'].update({'initialDate': first_slot.start_datetime})
        elif self.date_start and self.date_start >= datetime.date.today():
            action['context'].update({'initialDate': self.date_start})
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'tasks',
            'text': _lt('Planned'),
            'number': '%s Hours' % (self.total_forecast_time),
            'action_type': 'object',
            'action': 'action_project_forecast_from_project',
            'additional_context': json.dumps({
                'active_id': self.id,
            }),
            'show': self.allow_forecast,
            'sequence': 12,
        })
        return buttons
