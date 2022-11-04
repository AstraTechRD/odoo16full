# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_rental_order = fields.Boolean("Created In App Rental")
    rental_status = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('pickup', 'Confirmed'),
        ('return', 'Picked-up'),
        ('returned', 'Returned'),
        ('cancel', 'Cancelled'),
    ], string="Rental Status", compute='_compute_rental_status', store=True)
    # rental_status = next action to do basically, but shown string is action done.

    has_pickable_lines = fields.Boolean(compute="_compute_rental_status", store=True)
    has_returnable_lines = fields.Boolean(compute="_compute_rental_status", store=True)
    next_action_date = fields.Datetime(
        string="Next Action", compute='_compute_rental_status', store=True)

    has_late_lines = fields.Boolean(compute="_compute_has_late_lines")

    @api.depends('is_rental_order', 'next_action_date', 'rental_status')
    def _compute_has_late_lines(self):
        for order in self:
            order.has_late_lines = (
                order.is_rental_order
                and order.rental_status in ['pickup', 'return']  # has_pickable_lines or has_returnable_lines
                and order.next_action_date and order.next_action_date < fields.Datetime.now())

    @api.depends('state', 'order_line', 'order_line.product_uom_qty', 'order_line.qty_delivered', 'order_line.qty_returned')
    def _compute_rental_status(self):
        for order in self:
            if order.state in ['sale', 'done'] and order.is_rental_order:
                rental_order_lines = order.order_line.filtered(lambda l: l.is_rental and l.start_date and l.return_date)
                pickeable_lines = rental_order_lines.filtered(lambda sol: sol.qty_delivered < sol.product_uom_qty)
                returnable_lines = rental_order_lines.filtered(lambda sol: sol.qty_returned < sol.qty_delivered)
                min_pickup_date = min(pickeable_lines.mapped('start_date')) if pickeable_lines else 0
                min_return_date = min(returnable_lines.mapped('return_date')) if returnable_lines else 0
                if min_pickup_date and pickeable_lines and (not returnable_lines or min_pickup_date <= min_return_date):
                    order.rental_status = 'pickup'
                    order.next_action_date = min_pickup_date
                elif returnable_lines:
                    order.rental_status = 'return'
                    order.next_action_date = min_return_date
                else:
                    order.rental_status = 'returned'
                    order.next_action_date = False
                order.has_pickable_lines = bool(pickeable_lines)
                order.has_returnable_lines = bool(returnable_lines)
            else:
                order.has_pickable_lines = False
                order.has_returnable_lines = False
                order.rental_status = order.state if order.is_rental_order else False
                order.next_action_date = False

    # PICKUP / RETURN : rental.processing wizard

    def open_pickup(self):
        status = "pickup"
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        lines_to_pickup = self.order_line.filtered(
            lambda r: r.state in ['sale', 'done'] and r.is_rental and float_compare(r.product_uom_qty, r.qty_delivered, precision_digits=precision) > 0)
        return self._open_rental_wizard(status, lines_to_pickup.ids)

    def open_return(self):
        status = "return"
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        lines_to_return = self.order_line.filtered(
            lambda r: r.state in ['sale', 'done'] and r.is_rental and float_compare(r.qty_delivered, r.qty_returned, precision_digits=precision) > 0)
        return self._open_rental_wizard(status, lines_to_return.ids)

    def _open_rental_wizard(self, status, order_line_ids):
        context = {
            'order_line_ids': order_line_ids,
            'default_status': status,
            'default_order_id': self.id,
        }
        return {
            'name': _('Validate a pickup') if status == 'pickup' else _('Validate a return'),
            'view_mode': 'form',
            'res_model': 'rental.order.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        if self.is_rental_order:
            return self.env.ref('sale_renting.rental_order_action')
        else:
            return super()._get_portal_return_action()
