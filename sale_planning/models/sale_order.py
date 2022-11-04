# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models, fields, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    planning_hours_planned = fields.Float(compute='_compute_planning_hours')
    planning_hours_to_plan = fields.Float(compute='_compute_planning_hours')
    planning_first_sale_line_id = fields.Many2one('sale.order.line', compute='_compute_planning_first_sale_line_id')
    planning_initial_date = fields.Date(compute='_compute_planning_initial_date')

    @api.depends('order_line.planning_hours_to_plan', 'order_line.planning_hours_planned')
    def _compute_planning_hours(self):
        group_data = self.env['sale.order.line']._read_group([
            ('order_id', 'in', self.ids),
        ], ['order_id', 'planning_hours_to_plan', 'planning_hours_planned'], ['order_id'])
        mapped_data = defaultdict(lambda: {'planning_hours_to_plan': 0.0, 'planning_hours_planned': 0.0})
        mapped_data.update({
            data['order_id'][0]: {'planning_hours_to_plan': data['planning_hours_to_plan'], 'planning_hours_planned': data['planning_hours_planned']}
            for data in group_data
        })
        for order in self:
            order.planning_hours_planned = mapped_data[order.id]['planning_hours_planned']
            order.planning_hours_to_plan = mapped_data[order.id]['planning_hours_to_plan'] - mapped_data[order.id]['planning_hours_planned']

    @api.depends('order_line.product_id.planning_enabled', 'order_line.planning_hours_to_plan', 'order_line.planning_hours_planned')
    def _compute_planning_first_sale_line_id(self):
        planning_sol = self.env['sale.order.line'].search([
            ('order_id', 'in', self.ids),
            ('product_id.planning_enabled', '=', True),
            ('planning_hours_to_plan', '>', 0),
        ])
        mapped_data = defaultdict(lambda: self.env['sale.order.line'])
        for sol in planning_sol:
            if not mapped_data[sol.order_id]:
                if sol.planning_hours_to_plan > sol.planning_hours_planned:
                    mapped_data[sol.order_id] = sol
        for order in self:
            order.planning_first_sale_line_id = mapped_data[order]

    @api.depends('order_line.planning_slot_ids.start_datetime')
    def _compute_planning_initial_date(self):
        group_data = self.env['planning.slot']._read_group([
            ('sale_order_id', 'in', self.ids)
        ], ['sale_order_id', 'start_datetime:min'], ['sale_order_id'])
        mapped_data = {data['sale_order_id'][0]: data['start_datetime'] for data in group_data}
        for order in self:
            if mapped_data.get(order.id):
                order.planning_initial_date = mapped_data[order.id].date()
            else:
                order.planning_initial_date = False

    # -----------------------------------------------------------------
    # Action methods
    # -----------------------------------------------------------------

    def _action_confirm(self):
        """ On SO confirmation, some lines should generate a planning slot. """
        result = super()._action_confirm()
        self.order_line.sudo()._planning_slot_generation()
        return result

    def action_view_planning(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("planning.planning_action_schedule_by_resource")
        action.update({
            'name': _('View Planning'),
            'context': {
                'default_sale_line_id': self.planning_first_sale_line_id.id,
                'search_default_group_by_role': 1,
                'search_default_group_by_resource': 2,
                'initialDate': self.planning_initial_date,
                'planning_gantt_active_sale_order_id': self.id}
        })
        return action
