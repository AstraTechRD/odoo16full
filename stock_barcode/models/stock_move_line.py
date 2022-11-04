# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_barcode = fields.Char(related='product_id.barcode')
    location_processed = fields.Boolean()
    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')
    picking_location_id = fields.Many2one(related='picking_id.location_id')
    picking_location_dest_id = fields.Many2one(related='picking_id.location_dest_id')
    product_stock_quant_ids = fields.One2many('stock.quant', compute='_compute_product_stock_quant_ids')
    product_packaging_id = fields.Many2one(related='move_id.product_packaging_id')
    product_packaging_uom_qty = fields.Float('Packaging Quantity', compute='_compute_product_packaging_uom_qty', help="Quantity of the Packaging in the UoM of the Stock Move Line.")
    is_completed = fields.Boolean(compute='_compute_is_completed', help="Check if the quantity done matches the demand")

    @api.depends('product_id', 'product_id.stock_quant_ids')
    def _compute_product_stock_quant_ids(self):
        for line in self:
            line.product_stock_quant_ids = line.product_id.stock_quant_ids.filtered(lambda q: q.company_id in self.env.companies and q.location_id.usage == 'internal')

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _compute_product_packaging_uom_qty(self):
        for sml in self:
            sml.product_packaging_uom_qty = sml.product_packaging_id.product_uom_id._compute_quantity(sml.product_packaging_id.qty, sml.product_uom_id)

    @api.depends('qty_done')
    def _compute_is_completed(self):
        for line in self:
            line.is_completed = line.qty_done == line.reserved_uom_qty

    def _inverse_dummy_id(self):
        pass

    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'location_id',
            'location_dest_id',
            'qty_done',
            'display_name',
            'reserved_uom_qty',
            'product_uom_id',
            'product_barcode',
            'owner_id',
            'lot_id',
            'lot_name',
            'package_id',
            'result_package_id',
            'dummy_id',
            'product_packaging_id',
            'product_packaging_uom_qty',
        ]
