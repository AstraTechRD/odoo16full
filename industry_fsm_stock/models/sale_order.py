# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    fsm_lot_id = fields.Many2one('stock.lot', domain="[('product_id', '=', product_id)]")
