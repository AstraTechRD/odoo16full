# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductionLot(models.Model):
    _inherit = 'stock.lot'

    quality_check_qty = fields.Integer(
        compute='_compute_quality_check_qty', groups='quality.group_quality_user')

    def _compute_quality_check_qty(self):
        for prod_lot in self:
            prod_lot.quality_check_qty = self.env['quality.check'].search_count([
                ('lot_id', '=', prod_lot.id),
                ('company_id', '=', self.env.company.id)
            ])
