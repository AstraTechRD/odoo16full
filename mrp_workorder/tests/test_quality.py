# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestQuality(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_1 = cls.env['product.product'].create({'name': 'Table'})
        cls.product_2 = cls.env['product.product'].create({'name': 'Table top'})
        cls.product_3 = cls.env['product.product'].create({'name': 'Table leg'})
        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_1.id,
            'product_tmpl_id': cls.product_1.product_tmpl_id.id,
            'product_uom_id': cls.product_1.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'name': 'Assembly', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.product_3.id, 'product_qty': 4})
            ]
        })

    def test_quality_point_onchange(self):
        quality_point_form = Form(self.env['quality.point'].with_context(default_product_ids=[self.product_2.id]))
        # Form should keep the default products set
        self.assertEqual(len(quality_point_form.product_ids), 1)
        self.assertEqual(quality_point_form.product_ids[0].id, self.product_2.id)
        # <field name="operation_id" attrs="{'invisible': [('is_workorder_step', '=', False)]}"/>
        # @api.depends('operation_id', 'picking_type_ids')
        # def _compute_is_workorder_step(self):
        #     for quality_point in self:
        #         quality_point.is_workorder_step = quality_point.operation_id or quality_point.picking_type_ids and\
        #             all(pt.code == 'mrp_operation' for pt in quality_point.picking_type_ids)
        quality_point_form.picking_type_ids.add(
            self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        )
        # Select a workorder operation
        quality_point_form.operation_id = self.bom.operation_ids[0]
        # Product should be replaced by the product linked to the bom
        self.assertEqual(len(quality_point_form.product_ids), 1)
        self.assertEqual(quality_point_form.product_ids[0].id, self.bom.product_id.id)
