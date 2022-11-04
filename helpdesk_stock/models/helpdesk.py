# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    product_id = fields.Many2one('product.product', string='Product', tracking=True,
        domain="[('sale_ok', '=', True), ('id', 'in', suitable_product_ids), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Product this ticket is about. If selected, only the sales orders, deliveries and invoices including this product will be visible.")
    suitable_product_ids = fields.Many2many('product.product', compute='_compute_suitable_product_ids')
    has_partner_picking = fields.Boolean(compute='_compute_suitable_product_ids')
    tracking = fields.Selection(related='product_id.tracking')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', domain="[('product_id', '=', product_id)]", tracking=True)
    pickings_count = fields.Integer('Return Orders Count', compute="_compute_pickings_count")
    picking_ids = fields.Many2many('stock.picking', string="Return Orders", copy=False)

    @api.depends('partner_id')
    def _compute_suitable_product_ids(self):
        sale_data = self.env['sale.order.line']._read_group([
            ('product_id', '!=', False),
            ('order_id.state', '=', 'sale'),
            ('order_partner_id', 'in', self.mapped('partner_id').ids)
        ], ['order_partner_id', 'product_id:array_agg(product_id)'], ['order_partner_id'], lazy=False)
        order_data = {data['order_partner_id'][0]: data['product_id'] for data in sale_data}

        picking_data = self.env['stock.picking']._read_group([
            ('state', '=', 'done'),
            ('partner_id', 'in', self.mapped('partner_id').ids),
            ('picking_type_code', '=', 'outgoing'),
        ], ['ids:array_agg(id)', 'id'], ['partner_id'], lazy=False)

        picking_mapped_data = {data['partner_id'][0]: data['ids'] for data in picking_data}
        picking_ids = [picking for key, picking in picking_mapped_data.items()]
        outoing_product = {}
        if picking_ids and picking_ids[0]:
            move_line_data = self.env['stock.move.line']._read_group([
                ('state', '=', 'done'),
                ('picking_id', 'in', picking_ids[0]),
                ('picking_code', '=', 'outgoing'),
            ], ['product_id:array_agg(product_id)'], ['picking_id'], lazy=False)
            move_lines = {data['picking_id'][0]: data['product_id'] for data in move_line_data}
            if move_lines:
                for partner_id, picks in picking_mapped_data.items():
                    product_lists = [move_lines[pick] for pick in picks if pick in move_lines]
                    outoing_product.update({partner_id: list(itertools.chain(*product_lists))})

        for ticket in self:
            product_ids = set(order_data.get(ticket.partner_id.id, []) + outoing_product.get(ticket.partner_id.id, []))
            ticket.suitable_product_ids = [fields.Command.set(product_ids)]
            if ticket.product_id._origin not in ticket.suitable_product_ids._origin:
                ticket.product_id = False
            ticket.has_partner_picking = outoing_product.get(ticket.partner_id.id, False)

    @api.depends('picking_ids')
    def _compute_pickings_count(self):
        for ticket in self:
            ticket.pickings_count = len(ticket.picking_ids)

    def action_view_pickings(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Return Orders'),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': dict(self._context, create=False, default_company_id=self.company_id.id)
        }
        if self.pickings_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.picking_ids.id
            })
        return action
