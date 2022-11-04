# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class FsmStockTracking(models.TransientModel):
    _name = 'fsm.stock.tracking'
    _description = 'Track Stock'

    task_id = fields.Many2one('project.task')
    fsm_done = fields.Boolean(related='task_id.fsm_done')
    product_id = fields.Many2one('product.product')
    tracking = fields.Selection(related='product_id.tracking')

    tracking_line_ids = fields.One2many('fsm.stock.tracking.line', 'wizard_tracking_line')
    tracking_validated_line_ids = fields.One2many('fsm.stock.tracking.line', 'wizard_tracking_line_valided')
    company_id = fields.Many2one('res.company', 'Company')

    def generate_lot(self):
        self.ensure_one()
        if self.fsm_done:
            return

        if self.tracking_line_ids.filtered(lambda l: not l.lot_id):
            raise UserError(_('Each line needs a Lot/Serial Number'))

        SaleOrderLine = self.env['sale.order.line'].sudo()

        sale_lines_remove = SaleOrderLine.search([
            ('order_id', '=', self.task_id.sale_order_id.id),
            ('product_id', '=', self.product_id.id),
            ('id', 'not in', self.tracking_line_ids.sale_order_line_id.ids),
            ('task_id', '=', self.task_id.id)
        ])

        for line in self.tracking_line_ids:
            qty = line.quantity if self.tracking == 'lot' else 1
            if line.sale_order_line_id:
                line.sale_order_line_id.write({'fsm_lot_id': line.lot_id, 'product_uom_qty': qty + line.sale_order_line_id.qty_delivered})
            elif qty:
                vals = {
                    'order_id': self.task_id.sale_order_id.id,
                    'product_id': self.product_id.id,
                    'product_uom_qty': qty,
                    'task_id': self.task_id.id,
                    'fsm_lot_id': line.lot_id.id,
                }
                SaleOrderLine.create(vals)

        if self.task_id.sale_order_id.state == 'draft':
            sale_lines_remove.unlink()
        else:
            for sl in sale_lines_remove:
                sl.write({'product_uom_qty': sl.qty_delivered})


class FsmStockTrackingLine(models.TransientModel):
    _name = 'fsm.stock.tracking.line'
    _description = 'Lines for FSM Stock Tracking'

    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', domain="[('company_id', '=', company_id), ('product_id', '=', product_id)]")
    quantity = fields.Float(required=True, default=1)
    product_id = fields.Many2one('product.product')
    sale_order_line_id = fields.Many2one('sale.order.line')
    company_id = fields.Many2one('res.company', 'Company')
    wizard_tracking_line = fields.Many2one('fsm.stock.tracking', string="Tracking Line")
    wizard_tracking_line_valided = fields.Many2one('fsm.stock.tracking', string="Validated Tracking Line")
