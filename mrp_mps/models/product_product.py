# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    schedule_count = fields.Integer('Schedules', compute='_compute_schedule_count')

    def _compute_schedule_count(self):
        grouped_data = self.env['mrp.production.schedule'].read_group(
            [('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        schedule_counts = {}
        for data in grouped_data:
            schedule_counts[data['product_id'][0]] = data['product_id_count']
        for product in self:
            product.schedule_count = schedule_counts.get(product.id, 0)
