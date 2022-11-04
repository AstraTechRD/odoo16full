# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import api, fields, models

class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _default_color(self):
        return randint(1, 11)

    color = fields.Integer(default=_default_color)
    avatar_128 = fields.Image(compute='_compute_avatar_128')
    flexible_hours = fields.Boolean('Flexible Hours')
    role_ids = fields.Many2many('planning.role', 'resource_resource_planning_role_rel',
                                'resource_resource_id', 'planning_role_id', 'Roles')

    @api.depends('employee_id')
    def _compute_avatar_128(self):
        for resource in self:
            employees = resource.with_context(active_test=False).employee_id
            resource.avatar_128 = employees[0].avatar_128 if employees else False

    def get_formview_id(self, access_uid=None):
        if self.env.context.get('from_planning'):
            return self.env.ref('planning.resource_resource_with_employee_form_view_inherit', raise_if_not_found=False).id
        return super().get_formview_id(access_uid)

    @api.model_create_multi
    def create(self, vals_list):
        resources = super().create(vals_list)
        if self.env.context.get('from_planning'):
            create_vals = []
            for resource in resources.filtered(lambda r: r.resource_type == 'user'):
                create_vals.append({
                    'name': resource.name,
                    'resource_id': resource.id,
                })
            self.env['hr.employee'].sudo().with_context(from_planning=False).create(create_vals)
        return resources

    def name_get(self):
        if not self.env.context.get('show_job_title'):
            return super().name_get()
        return [(
            resource.id,
            resource.employee_id._get_employee_name_with_job_title() if resource.employee_id else resource.name,
        ) for resource in self]
