# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime

from odoo import api, models
from odoo.osv import expression

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _timesheet_create_project(self):
        return super(SaleOrderLine, self.with_context(default_allow_forecast=True))._timesheet_create_project()

    @api.depends('analytic_line_ids.unit_amount', 'analytic_line_ids.validated', 'planning_slot_ids.allocated_hours', 'task_id', 'project_id')
    def _compute_planning_hours_planned(self):
        PlanningSlot = self.env['planning.slot']
        planning_forecast_sols = self.filtered_domain([
            ('product_id.planning_enabled', '!=', False),
            '|', ('task_id.allow_timesheets', '=', True), ('project_id.allow_timesheets', '=', True),
        ])
        super(SaleOrderLine, self - planning_forecast_sols)._compute_planning_hours_planned()
        if planning_forecast_sols:
            # Search for validated timesheets, and the most recent date of validated timesheets
            group_unit_amount = self.env['account.analytic.line']._read_group([
                ('validated', '=', True),
                ('so_line', 'in', planning_forecast_sols.ids),
                ('project_id', '!=', False),
            ], ['so_line', 'unit_amount', 'date:max'], ['so_line'])
            mapped_unit_amount = defaultdict(float)
            planning_domain = []
            for data in group_unit_amount:
                # Build a domain to search for slots, for every SOL, beginning from the most recent validated timesheet
                tmp_domain = [
                    ('sale_line_id', '=', data['so_line'][0]),
                    ('start_datetime', '>', datetime.combine(data['date'], datetime.max.time())),
                ]
                planning_domain = expression.OR([planning_domain, tmp_domain])
                mapped_unit_amount[data['so_line'][0]] = data['unit_amount']
            sol_without_validated_aal = [item for item in planning_forecast_sols.ids if item not in mapped_unit_amount.keys()]
            if sol_without_validated_aal:
                # Fill the domain with SOL which doesn't have validated timesheets (so no start_datetime constraint)
                if planning_domain:
                    planning_domain = expression.OR([planning_domain, [('sale_line_id', 'in', sol_without_validated_aal), ('start_datetime', '!=', False)]])
                else:
                    planning_domain = [('sale_line_id', 'in', sol_without_validated_aal), ('start_datetime', '!=', False)]
            # Search for the allocated hours on the slots in the domain
            group_allocated_hours = PlanningSlot.with_context(sale_planning_prevent_recompute=True)._read_group(
                expression.AND([[('start_datetime', '!=', False)], planning_domain]),
                ['sale_line_id', 'allocated_hours'],
                ['sale_line_id'])
            mapped_allocated_hours = {data['sale_line_id'][0]: data['allocated_hours'] for data in group_allocated_hours}
            uom_hour = self.env.ref('uom.product_uom_hour')
            for sol in planning_forecast_sols:
                # Convert timesheeted unit amounts to hours
                converted_unit_amount = sol.company_id.project_time_mode_id._compute_quantity(mapped_unit_amount.get(sol.id, 0.0), uom_hour)
                # update the planning hours planned
                sol.planning_hours_planned = mapped_allocated_hours.get(sol.id, 0.0) + converted_unit_amount
            self.env.add_to_compute(PlanningSlot._fields['allocated_hours'], PlanningSlot.search([
                ('start_datetime', '=', False),
                ('sale_line_id', 'in', self.ids),
            ]))
