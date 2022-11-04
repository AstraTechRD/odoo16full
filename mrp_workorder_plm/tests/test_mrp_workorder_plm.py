# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.mrp_plm.tests.test_common import TestPlmCommon


class TestMrpWorkorderPlm(TestPlmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMrpWorkorderPlm, cls).setUpClass()
        cls.picking_type_manufacturing = cls.env.ref('stock.warehouse0').manu_type_id
        cls.quality_point_test1 = cls.env['quality.point'].create({
            'name': 'QP1',
            'product_ids': [(4, cls.table.id)],
            'picking_type_ids': [(4, cls.picking_type_manufacturing.id)],
            'operation_id': cls.bom_table.operation_ids[0].id,
            'test_type_id': cls.env.ref('quality.test_type_instructions').id,
        })
        cls.quality_point_test2 = cls.env['quality.point'].create({
            'name': 'QP2',
            'product_ids': [(4, cls.table.id)],
            'picking_type_ids': [(4, cls.picking_type_manufacturing.id)],
            'operation_id': cls.bom_table.operation_ids[0].id,
            'test_type_id': cls.env.ref('quality.test_type_instructions').id,
        })

    def test_operation_change(self):
        "Test eco with bom operation changes."
        # --------------------------------
        # Create ecos for bill of material.
        # ---------------------------------

        eco1 = self._create_eco('ECO1', self.bom_table, self.eco_type.id, self.eco_stage.id)

        # Start new revision of eco1
        eco1.action_new_revision()

        # -----------------------------------------
        # Check eco status after start new revision.
        # ------------------------------------------

        self.assertEqual(eco1.state, 'progress', "Wrong state on eco1.")

        # change quality_point_test1 type
        eco1.new_bom_id.operation_ids[0].quality_point_ids[0].test_type_id = self.env.ref('quality.test_type_picture')

        # remove quality_point_test2
        eco1.new_bom_id.operation_ids[0].quality_point_ids[1].unlink()

        # add quality_point_test3
        self.env['quality.point'].create({
            'name': 'QP3',
            'product_ids': [(4, self.table.id)],
            'picking_type_ids': [(4, self.picking_type_manufacturing.id)],
            'operation_id': eco1.new_bom_id.operation_ids[1].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
        })

        # Check correctness
        self.assertEqual(eco1.routing_change_ids[0].change_type, 'update', "Wrong type on opration change line.")
        self.assertEqual(eco1.routing_change_ids[1].change_type, 'remove', "Wrong type on opration change line.")
        self.assertEqual(eco1.routing_change_ids[2].change_type, 'add', "Wrong type on opration change line.")
