# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class MrpCostStructure(models.AbstractModel):
    _inherit = 'report.mrp_account_enterprise.mrp_cost_structure'

    def get_lines(self, productions):
        res = super().get_lines(productions)
        for vals in res:
            product = vals['product']
            mos = productions.filtered(lambda m: m.product_id == product)
            subcontracted_moves = mos._get_subcontract_move()
            if not subcontracted_moves:
                continue

            vals['subcontracting'] = []
            vals['subcontracting_total_cost'] = 0.0
            vals['subcontracting_total_qty'] = 0.0

            for subcontracted_move in subcontracted_moves:
                mos_subcontracted = subcontracted_move._get_subcontract_production()
                move_fin = mos_subcontracted.move_finished_ids.filtered(lambda m: m.state != 'cancel' and m.product_id == m.production_id.product_id)
                if not move_fin:
                    continue
                unit_cost = mos_subcontracted.extra_cost
                partner = subcontracted_move.partner_id or subcontracted_move.picking_id.partner_id
                vals['subcontracting'].append({
                    'cost': unit_cost * subcontracted_move.product_qty,
                    'qty': subcontracted_move.product_qty,
                    'unit_cost': unit_cost,
                    'uom': product.uom_id,
                    'partner_name': partner.display_name,
                })
                vals['subcontracting_total_cost'] += unit_cost * subcontracted_move.product_qty
                vals['subcontracting_total_qty'] += subcontracted_move.product_qty

            vals['total_cost'] += vals['subcontracting_total_cost']

        return res
