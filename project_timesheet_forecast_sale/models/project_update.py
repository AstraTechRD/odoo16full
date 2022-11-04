# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_services_values(self, project):
        services = super()._get_services_values(project)
        if not project.allow_billable or not project.allow_forecast:
            return services
        services['total_planned'] = 0
        sol_ids = [
            service['sol'].id
            for service in services['data']
        ]
        slots = self.env['planning.slot']._read_group([
            ('project_id', '=', project.id),
            ('sale_line_id', 'in', sol_ids),
            ('start_datetime', '>=', fields.Date.today())
        ], ['sale_line_id', 'allocated_hours'], ['sale_line_id'])
        slots_by_order_line = {res['sale_line_id'][0]: res['allocated_hours'] for res in slots}
        total_planned = 0
        uom_hour = self.env.ref('uom.product_uom_hour')
        for service in services['data']:
            allocated_hours = uom_hour._compute_quantity(slots_by_order_line.get(service['sol'].id, 0), self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
            service['planned_value'] = allocated_hours
            service['remaining_value'] = service['remaining_value'] - allocated_hours
            if service['sol'].product_uom.category_id == self.env.company.timesheet_encode_uom_id.category_id:
                total_planned += allocated_hours
        services['total_planned'] = total_planned
        services['total_remaining'] = services['total_remaining'] - services['total_planned']
        return services
