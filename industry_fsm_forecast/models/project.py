# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    allow_forecast = fields.Boolean(compute='_compute_allow_forecast', store=True, readonly=False)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'allow_forecast' in fields_list and defaults.get('is_fsm', False):
            defaults['allow_forecast'] = False
        return defaults

    @api.depends('is_fsm')
    def _compute_allow_forecast(self):
        for project in self:
            if not project._origin:
                project.allow_forecast = not project.is_fsm
