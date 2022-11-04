# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class MrpWorkorderAdditionalProduct(models.TransientModel):
    _name = "mrp_workorder.additional.product"
    _description = "Additional Product"

    product_id = fields.Many2one(
        'product.product',
        'Product',
        required=True,
        domain="[('company_id', 'in', (company_id, False)), ('type', '!=', 'service')]")
    product_tracking = fields.Selection(related='product_id.tracking')
    product_qty = fields.Float('Quantity', default=1, required=True)
    product_uom_id = fields.Many2one('uom.uom', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    type = fields.Selection([
        ('component', 'Component'),
        ('byproduct', 'By-Product')])
    workorder_id = fields.Many2one(
        'mrp.workorder', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    company_id = fields.Many2one(related='workorder_id.company_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            if self.product_tracking == 'serial':
                self.product_qty = 1

    def add_product(self):
        """Create workorder line for the additional product."""
        wo = self.workorder_id
        if self.type == 'component':
            test_type = self.env.ref('mrp_workorder.test_type_register_consumed_materials')
            move = self.env['stock.move'].create(
                wo.production_id._get_move_raw_values(
                    self.product_id,
                    self.product_qty,
                    self.product_id.uom_id,
                    operation_id=wo.operation_id.id,
                )
            )
        else:
            test_type = self.env.ref('mrp_workorder.test_type_register_byproducts')
            move = self.env['stock.move'].create(
                wo.production_id._get_move_finished_values(
                    self.product_id.id,
                    self.product_qty,
                    self.product_id.uom_id.id,
                    operation_id=wo.operation_id.id,
                )
            )

        move = move._action_confirm()
        check = {
            'workorder_id': wo.id,
            'component_id': self.product_id.id,
            'product_id': wo.product_id.id,
            'company_id': self.company_id.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            'finished_product_sequence': wo.qty_produced,
            'test_type_id': test_type.id,
            'qty_done': self.product_qty,
            'move_id': move.id,
        }
        additional_check = self.env['quality.check'].create(check)

        # Insert the quality check in the chain. The process is slightly different
        # if we are between two quality checks or at the summary step.
        if wo.current_quality_check_id:
            additional_check._insert_in_chain('before', wo.current_quality_check_id)
            wo._change_quality_check(position='previous')
        else:
            last_check = wo.check_ids.filtered(
                lambda c: not c.next_check_id and
                c.finished_product_sequence == wo.qty_produced and
                c != additional_check
            )
            additional_check._insert_in_chain('after', last_check)
            wo._change_quality_check(position='last')
