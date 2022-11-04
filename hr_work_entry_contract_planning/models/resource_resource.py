# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    flexible_hours = fields.Boolean(compute='_compute_flexible_hours', compute_sudo=True, readonly=False, store=True)

    @api.depends('employee_id.contract_id.work_entry_source')
    def _compute_flexible_hours(self):
        contract_read_group = self.env['hr.contract']._read_group(
            [
                ('employee_id', 'in', self.employee_id.ids),
                ('work_entry_source', 'in', ['attendance', 'planning']),
                ('state', '=', 'open'),
            ],
            ['employee_id'],
            ['employee_id'],
        )
        running_contract_count_per_employee_id = {res['employee_id'][0]: res['employee_id_count'] for res in contract_read_group}
        for resource in self:
            resource.flexible_hours = bool(running_contract_count_per_employee_id.get(resource.employee_id.id, 0))
