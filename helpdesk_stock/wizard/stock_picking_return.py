# -*- coding: utf-8 -*-
# Part of Odoo. See ICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    partner_id = fields.Many2one('res.partner', related="ticket_id.partner_id", string="Customer")
    ticket_id = fields.Many2one('helpdesk.ticket')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order',
        domain="[('order_line.product_id.type', '!=', 'service'), ('picking_ids.state', '=', 'done'), ('id', 'in', suitable_sale_order_ids)]",
        compute='_compute_sale_order_id', readonly=False)
    picking_id = fields.Many2one(domain="[('id', 'in', suitable_picking_ids)]", compute='_compute_picking_id', readonly=False, store=True)
    suitable_picking_ids = fields.Many2many('stock.picking', compute='_compute_suitable_picking_ids')
    suitable_sale_order_ids = fields.Many2many('sale.order', compute='_compute_suitable_sale_orders')

    @api.depends('picking_id')
    def _compute_sale_order_id(self):
        for r in self:
            r.sale_order_id = r.picking_id.sale_id

    @api.depends('sale_order_id')
    def _compute_picking_id(self):
        for r in self:
            if not r.picking_id:
                domain = [('state', '=', 'done'), ('partner_id', '=', r.ticket_id.partner_id.id)]
                if r.ticket_id.product_id:
                    domain += [('move_line_ids.product_id', '=', r.ticket_id.product_id.id)]
                picking = self.env['stock.picking'].search(domain, limit=1, order='id desc')
                if picking:
                    r.picking_id = picking
            if r.sale_order_id:
                r.picking_id = r.sale_order_id.picking_ids[0] if r.sale_order_id.picking_ids else False

    @api.depends('ticket_id.partner_id.commercial_partner_id', 'sale_order_id')
    def _compute_suitable_picking_ids(self):
        for r in self:
            domain = [('state', '=', 'done')]
            if r.sale_order_id:
                domain += [('id', 'in', r.sale_order_id.picking_ids._origin.ids)]
            elif r.partner_id:
                domain += [('partner_id', 'child_of', r.partner_id.commercial_partner_id._origin.id)]
            if r.ticket_id.product_id:
                domain += [('move_line_ids.product_id', '=', r.ticket_id.product_id._origin.id)]
            r.suitable_picking_ids = self.env['stock.picking'].search(domain)

    @api.depends('ticket_id.partner_id.commercial_partner_id')
    def _compute_suitable_sale_orders(self):
        for r in self:
            domain = [('state', '=', 'sale')]
            if r.ticket_id.product_id:
                domain += [('order_line.product_id', '=', r.ticket_id.product_id._origin.id)]
            if r.ticket_id.partner_id:
                domain += [('partner_id', 'child_of', r.ticket_id.partner_id.commercial_partner_id.id)]
            r.suitable_sale_order_ids = self.env['sale.order'].search(domain)

    def create_returns(self):
        res = super(ReturnPicking, self).create_returns()
        res['context'].update({'create': False})
        picking_id = self.env['stock.picking'].browse(res['res_id'])
        ticket_id = self.ticket_id or self.env['helpdesk.ticket'].sudo().search([('picking_ids', 'in', self.picking_id.id)], limit=1)
        if ticket_id:
            ticket_id.picking_ids |= picking_id
            picking_id.message_post_with_view('helpdesk.ticket_creation', values={'self': picking_id, 'ticket': ticket_id}, subtype_id=self.env.ref('mail.mt_note').id)
        return res
