# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    schedule_count = fields.Integer('Schedules', compute='_compute_schedule_count')

    def _compute_schedule_count(self):
        grouped_data = self.env['mrp.production.schedule'].read_group(
            [('product_id.product_tmpl_id', 'in', self.ids)], ['product_id'], ['product_id'])
        product_schedule_counts = {}
        for data in grouped_data:
            product_schedule_counts[data['product_id'][0]] = data['product_id_count']
        for template in self:
            schedule_count = 0
            for product_id in template.product_variant_ids.ids:
                schedule_count += product_schedule_counts.get(product_id, 0)
            template.schedule_count = schedule_count

    def action_open_mps_view(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_mps.action_mrp_mps")
        action['domain'] = [('product_id.product_tmpl_id', 'in', self.ids)]
        return action
