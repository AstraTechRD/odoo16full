# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests import common
from odoo.tests import Form
from odoo.exceptions import UserError


class TestWorkOrder(common.TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super(TestWorkOrder, cls).setUpClass()
        # Products and lots
        cls.submarine_pod = cls.env['product.product'].create({
            'name': 'Submarine pod',
            'type': 'product',
            'tracking': 'serial'})
        cls.sp1 = cls.env['stock.lot'].create({
            'product_id': cls.submarine_pod.id,
            'name': 'sp1',
            'company_id': cls.env.company.id,
        })
        cls.sp2 = cls.env['stock.lot'].create({
            'product_id': cls.submarine_pod.id,
            'name': 'sp2',
            'company_id': cls.env.company.id,
        })
        cls.sp3 = cls.env['stock.lot'].create({
            'product_id': cls.submarine_pod.id,
            'name': 'sp3',
            'company_id': cls.env.company.id,
        })
        cls.elon_musk = cls.env['product.product'].create({
            'name': 'Elon Musk',
            'type': 'product',
            'tracking': 'serial'})
        cls.elon1 = cls.env['stock.lot'].create({
            'product_id': cls.elon_musk.id,
            'name': 'elon1',
            'company_id': cls.env.company.id,
        })
        cls.elon2 = cls.env['stock.lot'].create({
            'product_id': cls.elon_musk.id,
            'name': 'elon2',
            'company_id': cls.env.company.id,
        })
        cls.elon3 = cls.env['stock.lot'].create({
            'product_id': cls.elon_musk.id,
            'name': 'elon3',
            'company_id': cls.env.company.id,
        })
        cls.metal_cylinder = cls.env['product.product'].create({
            'name': 'Metal cylinder',
            'type': 'product',
            'tracking': 'lot'})
        cls.mc1 = cls.env['stock.lot'].create({
            'product_id': cls.metal_cylinder.id,
            'name': 'mc1',
            'company_id': cls.env.company.id,
        })
        cls.trapped_child = cls.env['product.product'].create({
            'name': 'Trapped child',
            'type': 'product',
            'tracking': 'none'})
        # Bill of material
        cls.bom_submarine = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.submarine_pod.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                (0, 0, {'name': 'Weld Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 18, 'sequence': 2}),
            ]})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.elon_musk.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_submarine.id,
            'operation_id': cls.bom_submarine.operation_ids[1].id})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.trapped_child.id,
            'product_qty': 12.0,
            'bom_id': cls.bom_submarine.id})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.metal_cylinder.id,
            'product_qty': 2.0,
            'bom_id': cls.bom_submarine.id,
            'operation_id': cls.bom_submarine.operation_ids[0].id})
        cls.operation_4 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Rescue operation',
            'workcenter_id': cls.workcenter_1.id,
            'bom_id': cls.bom_submarine.id,
            'time_cycle': 13,
            'sequence': 2})
        #cls.mrp_routing_0 = cls.env['mrp.routing'].create({
        #    'name': 'Primary Assembly',
        #})
        #cls.mrp_routing_1 = cls.env['mrp.routing'].create({
        #    'name': 'Secondary Assembly',
        #})
        cls.mrp_workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Drill Station 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.mrp_workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        # --------------
        # .mrp_routing_0
        # --------------
#        cls.mrp_routing_workcenter_0 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_0.id,
#            'workcenter_id': cls.mrp_workcenter_3.id,
#            'name': 'Manual Assembly',
#            'time_cycle': 60,
#        })
#
#        # -------------
#        # mpr_routing_1
#        # -------------
#        cls.mrp_routing_workcenter_1 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_1.id,
#            'workcenter_id': cls.mrp_workcenter_3.id,
#            'name': 'Long time assembly',
#            'time_cycle': 180,
#            'sequence': 15,
#        })
#        cls.mrp_routing_workcenter_3 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_1.id,
#            'workcenter_id': cls.mrp_workcenter_3.id,
#            'name': 'Testing',
#            'time_cycle': 60,
#            'sequence': 10,
#        })
#        cls.mrp_routing_workcenter_4 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_1.id,
#            'workcenter_id': cls.mrp_workcenter_1.id,
#            'name': 'Packing',
#            'time_cycle': 30,
#            'sequence': 5,
#        })

        # Update quantities
        cls.location_1 = cls.env.ref('stock.stock_location_stock')
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.elon_musk, cls.location_1, 1.0, lot_id=cls.elon1)
        Quant._update_available_quantity(cls.elon_musk, cls.location_1, 1.0, lot_id=cls.elon2)
        Quant._update_available_quantity(cls.elon_musk, cls.location_1, 1.0, lot_id=cls.elon3)
        Quant._update_available_quantity(cls.metal_cylinder, cls.location_1, 6.0, lot_id=cls.mc1)
        Quant._update_available_quantity(cls.trapped_child, cls.location_1, 36.0)

    def test_assign_1(self):
        unit = self.ref("uom.product_uom_unit")
        self.stock_location = self.env.ref('stock.stock_location_stock')
        custom_laptop = self.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
        })
        custom_laptop.tracking = 'none'
        product_charger = self.env['product.product'].create({
            'name': 'Charger',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': unit,
            'uom_po_id': unit})
        product_keybord = self.env['product.product'].create({
            'name': 'Usb Keybord',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit})
        bom_custom_laptop = self.env['mrp.bom'].create({
            'product_tmpl_id': custom_laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': unit,
            #'routing_id': self.mrp_routing_0.id,
            # inlined mrp_routing0
            'bom_line_ids': [(0, 0, {
                'product_id': product_charger.id,
                'product_qty': 1,
                'product_uom_id': unit
            }), (0, 0, {
                'product_id': product_keybord.id,
                'product_qty': 1,
                'product_uom_id': unit
            })],
            'operation_ids': [(0, 0, {
                'workcenter_id': self.mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
            })]
        })

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = custom_laptop
        production_form.bom_id = bom_custom_laptop
        production_form.product_qty = 2
        production = production_form.save()
        production.action_confirm()
        production.button_plan()
        workorder = production.workorder_ids
        self.assertTrue(workorder)

        self.env['stock.quant']._update_available_quantity(product_charger, self.stock_location, 5)
        self.env['stock.quant']._update_available_quantity(product_keybord, self.stock_location, 5)

        production.action_assign()

    def test_flexible_consumption_1b(self):
        """ Production with a strict consumption
        Check that consuming a non tracked product more than planned triggers an error"""
        self.env['quality.point'].create({
            'product_ids': [(4, self.submarine_pod.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_submarine.operation_ids[0].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.trapped_child.id,
        })
        self.submarine_pod.tracking = 'lot'
        self.bom_submarine.bom_line_ids.filtered(lambda line: line.product_id == self.trapped_child).operation_id = self.bom_submarine.operation_ids[0]

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.bom_id = self.bom_submarine
        mo_form.product_qty = 2
        mo = mo_form.save()

        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        wo = mo.workorder_ids.sorted()[0]
        wo.button_start()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 2
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.trapped_child, 'The suggested component is wrong')
        self.assertEqual(qc_form.qty_done, 24, 'The suggested component qty_done is wrong')
        self.assertEqual(qc_form.component_remaining_qty, 24, 'The remaining quantity is wrong')
        # check the onchange on qty_producing is working
        qc = qc_form.save()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 12, 'The quantity done is wrong')
        self.assertEqual(qc_form.component_remaining_qty, 12, 'The remaining quantity is wrong')
        qc_form.save()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 2
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 24, 'The quantity done is wrong')
        self.assertEqual(qc_form.component_remaining_qty, 24, 'The remaining quantity is wrong')
        qc_form.qty_done = 12
        qc = qc_form.save()
        qc.action_continue()
        # Check the remaining quantity is well computed
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 12, 'The suggested component qty_done is wrong')
        self.assertEqual(qc_form.component_remaining_qty, 12, 'The remaining quantity is wrong')

    def test_flexible_consumption_1c(self):
        """ Production with a strict consumption
        Check that consuming the right amount of component doesn't trigger any error"""

        self.env['quality.point'].create({
            'product_ids': [(4, self.submarine_pod.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_submarine.operation_ids[0].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.trapped_child.id,
        })
        self.bom_submarine.bom_line_ids.filtered(lambda line: line.product_id == self.trapped_child).operation_id = self.bom_submarine.operation_ids[0]
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.bom_id = self.bom_submarine
        mo_form.product_qty = 1
        mo = mo_form.save()

        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()
        sorted_workorder_ids = mo.workorder_ids.sorted()
        wo = sorted_workorder_ids[0]
        wo.button_start()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 1)
        wo_form.finished_lot_id = self.sp1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 12, 'The suggested component qty_done is wrong')
        qc_form.qty_done = 6
        qc = qc_form.save()
        qc.action_continue()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.trapped_child, 'The suggested component is wrong')
        self.assertEqual(qc_form.qty_done, 6, 'The suggested component qty_done is wrong')
        qc = qc_form.save()
        qc._next()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 2, 'The suggested component qty_done is wrong')
        self.assertEqual(qc_form.lot_id, self.mc1, 'The suggested lot is wrong')
        qc_form.qty_done = 1
        qc = qc_form.save()
        qc.action_continue()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.metal_cylinder, 'The suggested component is wrong')
        self.assertEqual(qc_form.qty_done, 1, 'The suggested component qty_done is wrong')
        self.assertEqual(qc_form.lot_id, self.mc1, 'The suggested lot is wrong')
        qc = qc_form.save()
        qc._next()
        wo.do_finish()

        wo = sorted_workorder_ids[1]
        wo.button_start()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp1, 'The suggested final product is wrong')
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 1, 'The suggested qty_done should be one as the component is a serial number')
        # try to write on readonly field
        with self.assertRaises(AssertionError):
            qc_form.qty_done = 2
        self.assertEqual(qc_form.lot_id, self.elon1, 'The suggested lot is wrong')
        qc = qc_form.save()
        qc._next()
        wo.do_finish()

        wo = sorted_workorder_ids[2]
        wo.button_start()
        self.assertEqual(wo.finished_lot_id, self.sp1, 'The suggested final product is wrong')
        wo.do_finish()

        # Verify the reserved quantity has been split correctly
        self.assertEqual(mo.move_raw_ids.move_line_ids[1].reserved_uom_qty, 6.0, 'The reserved quantity is wrong')
        self.assertEqual(mo.move_raw_ids.move_line_ids[2].reserved_uom_qty, 6.0, 'The reserved quantity is wrong')
        self.assertEqual(mo.move_raw_ids.move_line_ids[3].reserved_uom_qty, 1.0, 'The reserved quantity is wrong')
        self.assertEqual(mo.move_raw_ids.move_line_ids[4].reserved_uom_qty, 1.0, 'The reserved quantity is wrong')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', 'Final state of the MO should be "done"')

    def test_flexible_consumption_2(self):
        """ Production with a flexible consumption
        Check that consuming different quantities than planned doensn't trigger
        any error"""
        self.bom_submarine.consumption = 'flexible'

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.bom_id = self.bom_submarine
        mo_form.product_qty = 1
        mo = mo_form.save()

        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        sorted_workorder_ids = mo.workorder_ids.sorted()
        wo = sorted_workorder_ids[0]
        wo.button_start()
        wo.finished_lot_id = self.sp1
        self.assertEqual(wo.current_quality_check_id.lot_id, self.mc1, 'The suggested lot is wrong')
        wo.current_quality_check_id.qty_done = 1
        wo.current_quality_check_id._next()
        wo.do_finish()

        wo = sorted_workorder_ids[1]
        wo.button_start()
        self.assertEqual(wo.finished_lot_id, self.sp1, 'The suggested final product is wrong')
        self.assertEqual(wo.current_quality_check_id.lot_id, self.elon1, 'The suggested lot is wrong')
        wo.current_quality_check_id.action_continue()
        wo.current_quality_check_id.lot_id = self.elon2
        wo.current_quality_check_id._next()
        wo.do_finish()

        wo = sorted_workorder_ids[2]
        wo.button_start()
        self.assertEqual(wo.finished_lot_id, self.sp1, 'The suggested final product is wrong')
        wo.do_finish()

        mo.button_mark_done()
        move_1 = mo.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder and move.state == 'done')
        self.assertEqual(sum(move_1.mapped('quantity_done')), 1, 'Only one cylinder was consumed')
        move_2 = mo.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk and move.state == 'done')
        self.assertEqual(sum(move_2.mapped('quantity_done')), 2, '2 Elon Musk was consumed')
        move_3 = mo.move_raw_ids.filtered(lambda move: move.product_id == self.trapped_child and move.state == 'done')
        self.assertEqual(sum(move_3.mapped('quantity_done')), 12, '12 child was consumed')
        self.assertEqual(mo.state, 'done', 'Final state of the MO should be "done"')

    def test_workorder_reservation_1(self):
        # Test multiple final lots management
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        production.action_confirm()
        production.action_assign()
        production.button_plan()
        sorted_workorder_ids = production.workorder_ids.sorted()
        wo = sorted_workorder_ids[0]
        wo.button_start()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.mc1, "component lot should be prefilled")
        self.assertEqual(qc_form.qty_done, 2, "component quantity should be prefilled")
        qc = qc_form.save()
        qc._next()
        wo.record_production()
        wo = sorted_workorder_ids[1]
        wo.button_start()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.elon1, "component lot should be prefilled")
        self.assertEqual(qc_form.qty_done, 1, "component quantity should be prefilled")
        qc = qc_form.save()
        qc._next()
        wo.record_production()
        wo = sorted_workorder_ids[2]
        wo.button_start()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp1, "final lot should be prefilled")
        wo = wo_form.save()
        wo.do_finish()
        production.button_mark_done()

        move_elon = production.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk)
        self.assertEqual(move_elon.state, 'done', 'Move should be done')
        self.assertEqual(move_elon.quantity_done, 1, 'Consumed quantity should be 2')
        self.assertEqual(len(move_elon.move_line_ids), 1, 'their should be 2 move lines')
        self.assertEqual(move_elon.move_line_ids.lot_id, self.elon1, 'Wrong serial number used')
        move_cylinder = production.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder)
        self.assertEqual(move_cylinder.state, 'done', 'Move should be done')
        self.assertEqual(move_cylinder.quantity_done, 2, 'Consumed quantity should be 4')
        move_child = production.move_raw_ids.filtered(lambda move: move.product_id == self.trapped_child)
        self.assertEqual(move_child.state, 'done', 'Move should be done')
        self.assertEqual(move_child.quantity_done, 12, 'Consumed quantity should be 24')

    def test_workorder_reservation_2(self):
        # Test multiple final product tracked by sn and all consumption in the same
        # workorder.

        # Also test assignment after workorder planning

        self.bom_submarine.bom_line_ids.write({
            'operation_id': False,
        })
        self.bom_submarine.operation_ids = False
        self.bom_submarine.write({
            'operation_ids': [(0, 0, {
                'workcenter_id': self.mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
            })]
        })

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 2
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()
        production.action_assign()
        production.workorder_ids.button_start()
        wo_form = Form(production.workorder_ids, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp1
        self.assertEqual(wo_form.qty_producing, 1, "Quantity to produce should prefilled with 1 (serial tracked product)")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.elon1, "component lot should be prefilled")
        self.assertEqual(qc_form.qty_done, 1, "component quantity should be 1 as final product is tracked")
        self.assertEqual(qc_form.component_remaining_qty, 1, "It needs 2 component")
        qc = qc_form.save()
        wo.current_quality_check_id._next()
        wo_form = Form(production.workorder_ids, view='mrp_workorder.mrp_workorder_view_form_tablet')
        qc_form = Form(production.workorder_ids.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.mc1, "qcrkorder should consume the second product")
        self.assertEqual(qc_form.qty_done, 2, "Quantity to consume should prefilled with 2")
        self.assertEqual(qc_form.component_id, self.metal_cylinder, "qcrkorder should be consume the second product")
        qc = qc_form.save()
        wo.current_quality_check_id._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp2
        self.assertEqual(wo_form.qty_producing, 1, "Quantity to produce should prefilled with 1 (serial tracked product)")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.elon2, "component lot should be prefilled")
        self.assertEqual(qc_form.qty_done, 1, "component quantity should be 1 as final product is tracked")
        qc = qc_form.save()
        self.assertEqual(wo.qty_production, 1, "Quantity to produce should be 2")
        qc._next()
        qc_form = Form(self.env['mrp.workorder'].browse(action['res_id']).current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.mc1, "qcrkorder should consume the second product")
        self.assertEqual(qc_form.qty_done, 2, "Quantity to consume should prefilled with 2")
        self.assertEqual(qc_form.component_id, self.metal_cylinder, "qcrkorder should be consume the second product")
        qc = qc_form.save()
        qc._next()
        wo.do_finish()
        productions = production.procurement_group_id.mrp_production_ids
        productions.button_mark_done()

        move_elon = productions.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk)
        self.assertEqual(move_elon.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_elon.mapped('quantity_done')), 2, 'Consumed quantity should be 2')
        self.assertEqual(len(move_elon.move_line_ids), 2, 'their should be 2 move lines')
        self.assertEqual(move_elon.move_line_ids.mapped('lot_id'), self.elon1 | self.elon2, 'Wrong serial numbers used')
        move_cylinder = productions.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder)
        self.assertEqual(move_cylinder.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_cylinder.mapped('quantity_done')), 4, 'Consumed quantity should be 4')
        move_child = productions.move_raw_ids.filtered(lambda move: move.product_id == self.trapped_child)
        self.assertEqual(move_child.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_child.mapped('quantity_done')), 24, 'Consumed quantity should be 24')

    def test_workorder_reservation_3(self):
        """ Test quantities suggestions make the whole production in only 1 workorder """
        self.bom_submarine.operation_ids = False
        self.bom_submarine.write({
            'operation_ids': [(0, 0, {
                'workcenter_id': self.workcenter_1.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
                'sequence': 5,
            })],
        })
        self.bom_submarine.bom_line_ids.write({'operation_id': self.bom_submarine.operation_ids.id})
        self.bom_submarine.bom_line_ids.filtered(lambda line: line.product_id == self.elon_musk).product_qty = 2
        self.bom_submarine.bom_line_ids.filtered(lambda line: line.product_id == self.metal_cylinder).product_qty = 3
        self.bom_submarine.bom_line_ids.filtered(lambda line: line.product_id == self.trapped_child).unlink()
        self.mc2 = self.env['stock.lot'].create({
            'product_id': self.metal_cylinder.id,
            'name': 'mc2',
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.metal_cylinder, self.location_1, -5.0, lot_id=self.mc1)
        self.env['stock.quant']._update_available_quantity(self.metal_cylinder, self.location_1, 2.0, lot_id=self.mc2)

        mrp_order_form = Form(self.env['mrp.production'])
        self.submarine_pod.tracking = 'none'
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        production.action_confirm()
        production.action_assign()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids), 1, "wrong number of workorders")
        self.assertEqual(production.workorder_ids[0].state, 'ready', "workorder state should be 'ready'")

        production.workorder_ids[0].button_start()
        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 0, "Wrong quantity to produce")
        wo_form.qty_producing = 1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.elon_musk, "The component should be changed")
        self.assertEqual(qc_form.lot_id, self.elon1, "The component should be changed")
        self.assertEqual(qc_form.qty_done, 1, "Wrong suggested quantity")
        qc = qc_form.save()
        qc.action_continue()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.elon2, "The component should be changed")
        self.assertEqual(qc_form.qty_done, 1, "Wrong suggested quantity")
        qc = qc_form.save()
        qc._next()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.metal_cylinder, "The component should be changed")
        self.assertEqual(qc_form.lot_id, self.mc1, "wrong suggested lot")
        self.assertEqual(qc_form.qty_done, 1, "wrong suggested quantity")
        qc = qc_form.save()
        qc.action_continue()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.lot_id, self.mc2, "Wrong suggested lot")
        self.assertEqual(qc_form.qty_done, 2, "Wrong suggested quantity")
        qc = qc_form.save()
        qc._next()
        wo.do_finish()
        production.button_mark_done()

        move_elon = production.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk)
        self.assertEqual(move_elon.state, 'done', 'Move should be done')
        self.assertEqual(move_elon.quantity_done, 2, 'Consumed quantity should be 2')
        self.assertEqual(len(move_elon.move_line_ids), 2, 'their should be 2 move lines')
        self.assertEqual(move_elon.move_line_ids.mapped('lot_id'), self.elon1 | self.elon2, 'Wrong serial numbers used')
        move_cylinder = production.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder)
        self.assertEqual(move_cylinder.state, 'done', 'Move should be done')
        self.assertEqual(move_cylinder.quantity_done, 3, 'Consumed quantity should be 4')
        self.assertEqual(move_cylinder.move_line_ids.mapped('lot_id'), self.mc1 | self.mc2, 'Wrong serial numbers used')

    def test_workorder_1(self):
        # get the computer sc234 demo data
        prod = self.submarine_pod
        bom = self.bom_submarine

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        # plan the work orders
        production.button_plan()

    def test_workorder_2(self):
        # Test multiple final lots management
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 3
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()
        sorted_workorder_ids = production.workorder_ids.sorted()
        self.assertEqual(len(production.workorder_ids), 3, "wrong number of workorders")
        self.assertEqual(sorted_workorder_ids[0].state, 'ready', "workorder state should be 'ready'")
        self.assertEqual(sorted_workorder_ids[1].state, 'pending', "workorder state should be 'pending'")

        sorted_workorder_ids[0].button_start()
        wo_form = Form(sorted_workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id.id, False, "final lot should be empty")
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo_form.finished_lot_id = self.sp1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 2, "Wrong quantity to consume")
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp2
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 2, "Wrong quantity to consume")
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp3
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 2, "Wrong quantity to consume")
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        wo.do_finish()

        sorted_workorder_ids_2 = production.procurement_group_id.mrp_production_ids[1].workorder_ids.sorted()
        sorted_workorder_ids_3 = production.procurement_group_id.mrp_production_ids[2].workorder_ids.sorted()
        sorted_workorder_ids[1].button_start()
        wo_form = Form(sorted_workorder_ids[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp1, "final lot should be prefilled")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon1
        qc = qc_form.save()
        qc._next()
        wo.record_production()
        sorted_workorder_ids_2[1].button_start()
        wo_form = Form(sorted_workorder_ids_2[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp2, "final lot should be prefilled")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon2
        qc = qc_form.save()
        qc._next()
        wo.record_production()
        sorted_workorder_ids_3[1].button_start()
        wo_form = Form(sorted_workorder_ids_3[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp3, "final lot should be prefilled")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon3
        qc = qc_form.save()
        qc._next()
        wo.do_finish()

        sorted_workorder_ids[2].button_start()
        wo_form = Form(sorted_workorder_ids[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp1, "final lot should be prefilled")
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo = wo_form.save()
        wo.record_production()
        sorted_workorder_ids_2[2].button_start()
        wo_form = Form(sorted_workorder_ids_2[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp2, "final lot should be prefilled")
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo = wo_form.save()
        wo.record_production()
        sorted_workorder_ids_3[2].button_start()
        wo_form = Form(sorted_workorder_ids_3[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, self.sp3, "final lot should be prefilled")
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo = wo_form.save()
        wo.do_finish()
        productions = production.procurement_group_id.mrp_production_ids
        productions.button_mark_done()

        move_elon = productions.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk)
        self.assertEqual(move_elon.mapped('state'), ['done'] * 3, 'Move should be done')
        self.assertEqual(sum(move_elon.mapped('quantity_done')), 3, 'Consumed quantity should be 2')
        self.assertEqual(len(move_elon.move_line_ids), 3, 'their should be 2 move lines')
        self.assertEqual(move_elon.move_line_ids.mapped('lot_id'), self.elon1 | self.elon2 | self.elon3, 'Wrong serial numbers used')
        self.assertEqual(move_elon.move_line_ids.produce_line_ids.lot_id, self.sp1 | self.sp2 | self.sp3, 'Wrong produced serial numbers')
        move_cylinder = productions.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder)
        self.assertEqual(move_cylinder.mapped('state'), ['done'] * 3, 'Move should be done')
        self.assertEqual(sum(move_cylinder.mapped('quantity_done')), 6, 'Consumed quantity should be 4')
        self.assertEqual(move_cylinder.move_line_ids.produce_line_ids.lot_id, self.sp1 | self.sp2 | self.sp3, 'Wrong produced serial numbers')
        move_child = productions.move_raw_ids.filtered(lambda move: move.product_id == self.trapped_child)
        self.assertEqual(move_child.mapped('state'), ['done'] * 3, 'Move should be done')
        self.assertEqual(sum(move_child.mapped('quantity_done')), 36, 'Consumed quantity should be 24')
        self.assertEqual(len(move_child.move_line_ids), 3, 'Their should be 3 move line as production was made in 3 steps')
        self.assertEqual(move_child.move_line_ids.produce_line_ids.lot_id, self.sp1 | self.sp2 | self.sp3, 'Wrong produced serial numbers')

    def test_workorder_3(self):
        # Test multiple final lots management
        # Required for `byproduct_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_byproducts')
        self.angry_british_diver = self.env['product.product'].create({
            'name': 'Angry Bristish Driver',
            'description': 'can stick his submarine where it hurts',
            'type': 'product',
            'tracking': 'serial'
        })
        self.abd_1 = self.env['stock.lot'].create({
            'product_id': self.angry_british_diver.id,
            'name': 'abd_1',
            'company_id': self.env.company.id,
        })
        self.abd_2 = self.env['stock.lot'].create({
            'product_id': self.angry_british_diver.id,
            'name': 'abd_2',
            'company_id': self.env.company.id,
        })

        self.advertising = self.env['product.product'].create({
            'name': 'Advertising',
            'type': 'product',
            'tracking': 'lot',
        })
        self.advertise_1 = self.env['stock.lot'].create({
            'product_id': self.advertising.id,
            'name': 'Good Advertise',
            'company_id': self.env.company.id,
        })
        self.advertise_2 = self.env['stock.lot'].create({
            'product_id': self.advertising.id,
            'name': 'bad Advertise',
            'company_id': self.env.company.id,
        })
        submarine_pod_bom_form = Form(self.bom_submarine)
        with submarine_pod_bom_form.byproduct_ids.new() as bp:
            bp.product_id = self.angry_british_diver
            bp.product_qty = 1.0
            bp.operation_id = self.bom_submarine.operation_ids[1]
        with submarine_pod_bom_form.byproduct_ids.new() as bp:
            bp.product_id = self.advertising
            bp.product_qty = 2.0
        submarine_pod_bom_form.save()

        mrp_order_form = Form(self.env['mrp.production'])
        self.submarine_pod.tracking = 'none'
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 2
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()
        sorted_workorder_ids = production.workorder_ids.sorted()
        self.assertEqual(len(production.workorder_ids), 3, "wrong number of workorders")
        self.assertEqual(sorted_workorder_ids[0].state, 'ready', "workorder state should be 'ready'")
        self.assertEqual(sorted_workorder_ids[1].state, 'pending', "workorder state should be 'pending'")

        sorted_workorder_ids[0].button_start()
        wo_form = Form(sorted_workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 0, "Wrong quantity to produce")
        wo_form.qty_producing = 1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.mc1
        self.assertEqual(qc_form.qty_done, 2, "Wrong quantity to consume")
        wo.current_quality_check_id._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity remaining")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 2, "Wrong quantity to consume")
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        wo.do_finish()

        sorted_workorder_ids[1].button_start()
        wo_form = Form(sorted_workorder_ids[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo = wo_form.save()
        qc_form = Form(sorted_workorder_ids[1].current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon1
        qc = qc_form.save()
        qc._next()
        # By-product management
        qc_form = Form(sorted_workorder_ids[1].current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.angry_british_diver)
        qc_form.lot_id = self.abd_1
        qc = qc_form.save()
        qc._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')

        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity remaining")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon2
        qc = qc_form.save()
        qc._next()
        # By-product management
        qc_form = Form(self.env['mrp.workorder'].browse(action['res_id']).current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.angry_british_diver)
        qc_form.lot_id = self.abd_2
        qc = qc_form.save()
        qc._next()
        wo.do_finish()

        sorted_workorder_ids[2].button_start()
        wo_form = Form(sorted_workorder_ids[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce (serial tracked)")
        wo = wo_form.save()
        qc_form = Form(sorted_workorder_ids[2].current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.qty_done = 2.0
        self.assertEqual(qc_form.component_id, self.advertising, "Wrong product")
        qc_form.lot_id = self.advertise_1
        qc = qc_form.save()
        qc._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_producing, 1, "Wrong quantity to produce")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.advertising, "Wrong product")
        qc_form.qty_done = 2.0
        qc_form.lot_id = self.advertise_2
        qc = qc_form.save()
        qc._next()
        wo.do_finish()
        productions = production.procurement_group_id.mrp_production_ids
        productions.button_mark_done()

        move_elon = productions.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk)
        self.assertEqual(move_elon.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_elon.mapped('quantity_done')), 2, 'Consumed quantity should be 2')
        self.assertEqual(len(move_elon.move_line_ids), 2, 'their should be 2 move lines')
        self.assertEqual(move_elon.move_line_ids.mapped('lot_id'), self.elon1 | self.elon2, 'Wrong serial numbers used')
        move_cylinder = productions.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder)
        self.assertEqual(move_cylinder.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_cylinder.mapped('quantity_done')), 4, 'Consumed quantity should be 4')
        move_child = productions.move_raw_ids.filtered(lambda move: move.product_id == self.trapped_child)
        self.assertEqual(move_child.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_child.mapped('quantity_done')), 24, 'Consumed quantity should be 24')
        self.assertEqual(len(move_child.move_line_ids), 2, 'Their should be 2 move lines as their are two production')
        move_byproduct_angry_british_diver = productions.move_finished_ids.filtered(lambda move: move.product_id == self.angry_british_diver)
        self.assertEqual(move_byproduct_angry_british_diver.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_byproduct_angry_british_diver.mapped('quantity_done')), 2, 'Consumed quantity should be 2')
        self.assertEqual(len(move_byproduct_angry_british_diver.move_line_ids), 2, 'Their should be 2 move lines')
        self.assertEqual(move_byproduct_angry_british_diver.move_line_ids.mapped('lot_id'), self.abd_1 | self.abd_2, 'Wrong serial numbers used')
        move_byproduct_advertising = productions.move_finished_ids.filtered(lambda move: move.product_id == self.advertising)
        self.assertEqual(move_byproduct_advertising.mapped('state'), ['done'] * 2, 'Move should be done')
        self.assertEqual(sum(move_byproduct_advertising.mapped('quantity_done')), 4, 'Consumed quantity should be 2')
        self.assertEqual(len(move_byproduct_advertising.move_line_ids), 2, 'Their should be 2 move lines')
        self.assertEqual(move_byproduct_advertising.move_line_ids.mapped('lot_id'), self.advertise_1 | self.advertise_2, 'Wrong serial numbers used')

    def test_workorder_4(self):
        """Produce 1 unit in a workorder with lot1, 2 units of this lot1 in the
        second workorder. Come back to the WO 1 and try to produce something else
        than lot1. It should raise an error """

        self.bom_submarine.bom_line_ids.write({'operation_id': False})
        # Use 'Secondary assembly routing (3 operations)'
        self.bom_submarine.write({
            'operation_ids': [
                (6, 0, 0),
                (0, 0, {'name': 'Long time assembly',
                        'workcenter_id': self.mrp_workcenter_3.id,
                        'time_cycle': 180,
                        'sequence': 15,
                        }),
                (0, 0, {'workcenter_id': self.mrp_workcenter_3.id,
                        'name': 'Testing',
                        'time_cycle': 60,
                        'sequence': 10,
                        }),
                (0, 0, {'workcenter_id': self.mrp_workcenter_3.id,
                        'name': 'Testing',
                        'time_cycle': 60,
                        'sequence': 10,
                        }),
            ],
        })

        self.submarine_pod.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'product_id': self.submarine_pod.id,
            'name': 'lot1',
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'product_id': self.submarine_pod.id,
            'name': 'lot2',
            'company_id': self.env.company.id,
        })

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 2
        production = mrp_order_form.save()
        production.action_confirm()
        production.button_plan()
        sorted_workorder_ids = production.workorder_ids.sorted()
        self.assertEqual(len(sorted_workorder_ids), 3, "wrong number of workorders")

        sorted_workorder_ids[0].button_start()
        wo_form = Form(sorted_workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 1
        wo_form.finished_lot_id = lot1
        wo = wo_form.save()
        wo.record_production()
        self.assertEqual(production.lot_producing_id, lot1)

        sorted_workorder_ids[1].button_start()
        wo_form = Form(sorted_workorder_ids[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_remaining, 1, "it left 1 quantity to produce")
        self.assertEqual(wo_form.qty_producing, 1, "it suggest 1 quantity to produce")
        self.assertEqual(wo_form.finished_lot_id, lot1, "Final lot should be the one entered in previous wo")
        wo_form.finished_lot_id = lot1
        wo_form.qty_producing = 2
        wo = wo_form.save()
        wo.record_production()

        sorted_workorder_ids_2 = production.procurement_group_id.mrp_production_ids[1].workorder_ids.sorted()
        wo_form = Form(sorted_workorder_ids_2[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_remaining, 1, "it left 1 quantity to produce")
        self.assertEqual(wo_form.qty_producing, 1, "it suggest 1 quantity to produce")
        wo_form.finished_lot_id = lot2
        wo_form.qty_producing = 1
        wo = wo_form.save()
        wo.record_production()
        backorder = production.procurement_group_id.mrp_production_ids[1]
        self.assertEqual(production.lot_producing_id, lot1)
        self.assertEqual(backorder.lot_producing_id, lot2)

    def test_workorder_5(self):
        """Test production of 2 lots in one workorder then check than the workorder
        line are well split in the second"""

        self.bom_submarine.bom_line_ids.write({'operation_id': False})
        # Use 'Secondary assembly routing (3 operations)'
        #self.bom_submarine.routing_id = self.mrp_routing_1

        self.bom_submarine.write({
            'operation_ids': [
                (6, 0, 0),
                (0, 0, {'name': 'Long time assembly',
                        'workcenter_id': self.mrp_workcenter_3.id,
                        'time_cycle': 180,
                        'sequence': 15,
                        }),
                (0, 0, {'workcenter_id': self.mrp_workcenter_3.id,
                        'name': 'Testing',
                        'time_cycle': 60,
                        'sequence': 10,
                        }),
                (0, 0, {'workcenter_id': self.mrp_workcenter_3.id,
                        'name': 'Testing',
                        'time_cycle': 60,
                        'sequence': 10,
                        }),
            ],
        })
        self.submarine_pod.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'product_id': self.submarine_pod.id,
            'name': 'lot1',
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'product_id': self.submarine_pod.id,
            'name': 'lot2',
            'company_id': self.env.company.id,
        })

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 2
        production = mrp_order_form.save()
        production.action_confirm()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids), 3, "wrong number of workorders")

        sorted_workorder_ids = production.workorder_ids.sorted()

        sorted_workorder_ids[0].button_start()
        wo_form = Form(sorted_workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 1
        wo_form.finished_lot_id = lot1
        wo = wo_form.save()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = lot2
        wo = wo_form.save()
        wo.record_production()

        sorted_workorder_ids[1].button_start()
        wo_form = Form(sorted_workorder_ids[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_remaining, 1, "it left 1 quantity to produce")
        self.assertEqual(wo_form.qty_producing, 1, "it suggest 1 quantity to produce")
        self.assertEqual(wo_form.finished_lot_id, lot1, "Final lot should be the one entered in previous wo")
        wo = wo_form.save()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_remaining, 1, "it left 1 quantity to produce")
        self.assertEqual(wo_form.qty_producing, 1, "it suggest 1 quantity to produce")
        self.assertEqual(wo_form.finished_lot_id, lot2, "Final lot should be the one entered in previous wo")
        wo = wo_form.save()
        wo.record_production()

        sorted_workorder_ids[2].button_start()
        wo_form = Form(sorted_workorder_ids[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.qty_remaining, 1, "it left 1 quantity to produce")
        self.assertEqual(wo_form.qty_producing, 1, "it suggest 1 quantity to produce")
        self.assertEqual(wo_form.finished_lot_id, lot1, "Final lot should be the one entered in previous wo")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.elon_musk, "Should be a register component check")
        self.assertEqual(qc_form.qty_done, 1, "Component is serial tracked")
        self.assertEqual(qc_form.component_remaining_qty, 1, "Qty_producing is 1")
        qc_form.lot_id = self.elon1
        qc = qc_form.save()
        qc._next()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.metal_cylinder, "Should be a register component check")
        self.assertEqual(qc_form.qty_done, 2, "2 components to produce")
        self.assertEqual(qc_form.component_remaining_qty, 2, "Qty_producing is 1")
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        action = wo.record_production()
        wo_form = Form(self.env['mrp.workorder'].browse(action['res_id']), view='mrp_workorder.mrp_workorder_view_form_tablet')
        self.assertEqual(wo_form.finished_lot_id, lot2, "Final lot should be the one entered in previous wo")
        self.assertEqual(wo_form.qty_remaining, 1, "it left 1 quantity to produce")
        self.assertEqual(wo_form.qty_producing, 1, "it suggest 1 quantity to produce")
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.elon_musk, "Should be a register component check")
        self.assertEqual(qc_form.qty_done, 1, "Component is serial tracked")
        self.assertEqual(qc_form.component_remaining_qty, 1, "Qty_producing is 1")
        qc_form.lot_id = self.elon2
        qc = qc_form.save()
        qc._next()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.metal_cylinder, "Should be a register component check")
        self.assertEqual(qc_form.qty_done, 2, "Component is serial tracked")
        self.assertEqual(qc_form.component_remaining_qty, 2, "Qty_producing is 1")
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        wo.record_production()

    def test_workorder_duplicate_sn(self):
        """produce a finished product tracked by serial number 2 times with the
        same SN. Check that an error is raised the second time"""

        self.bom_submarine.bom_line_ids.write({'operation_id': False})
        # Use 'Secondary assembly routing (3 operations)'
        self.bom_submarine.operation_ids = False
        self.bom_submarine.write({
            'operation_ids': [(0, 0, {
                'workcenter_id': self.mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
            })]
        })
        #self.bom_submarine.routing_id = self.mrp_routing_0
        self.submarine_pod.tracking = 'serial'
        sn1 = self.env['stock.lot'].create({
            'product_id': self.submarine_pod.id,
            'name': 'sn1',
            'company_id': self.env.company.id,
        })
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()
        production.action_confirm()
        production.button_plan()
        production.workorder_ids[0].button_start()
        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = sn1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon1
        qc = qc_form.save()
        qc._next()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.mc1
        qc = qc_form.save()
        qc._next()
        wo.do_finish()
        production.button_mark_done()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        production = mrp_order_form.save()
        production.action_confirm()
        production.button_plan()

        production.workorder_ids[0].button_start()
        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = sn1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.elon1
        qc = qc_form.save()
        with self.assertRaises(UserError):
            qc._next()
            wo.record_production()

    def test_post_inventory(self):
        """Test production of 2 finished products in one by one and posting intermediate inventory
        between the two production"""
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 2
        production = mrp_order_form.save()
        production.action_confirm()
        production.action_assign()
        production.button_plan()
        self.assertEqual(len(production.move_raw_ids), 3, "wrong number of raw moves")

        sorted_workorder_ids = production.workorder_ids.sorted()
        sorted_workorder_ids[0].button_start()
        wo_form = Form(sorted_workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp1
        wo = wo_form.save()
        wo.current_quality_check_id._next()
        wo.record_production()

        sorted_workorder_ids[1].button_start()
        wo_form = Form(sorted_workorder_ids[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo = wo_form.save()
        wo.current_quality_check_id._next()
        wo.record_production()

        sorted_workorder_ids[2].button_start()
        wo_form = Form(sorted_workorder_ids[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo = wo_form.save()
        wo.record_production()
        production._post_inventory()
        self.assertEqual(len(production.move_raw_ids), 3, "wrong number of raw moves")

        done_raw_moves = production.move_raw_ids.filtered(lambda move: move.state == 'done')
        self.assertEqual(len(done_raw_moves), 3, "wrong number of done raw moves")
        self.assertEqual(done_raw_moves[0].quantity_done, 1, "Components are not consumed")
        self.assertEqual(done_raw_moves[1].quantity_done, 12, "Components are not consumed")
        self.assertEqual(done_raw_moves[2].quantity_done, 2, "Components are not consumed")

        self.assertEqual(len(production.procurement_group_id.mrp_production_ids), 2)
        backorder = production.procurement_group_id.mrp_production_ids[-1]
        backorder.action_assign()

        assigned_raw_moves = backorder.move_raw_ids.filtered(lambda move: move.state == 'assigned')
        self.assertEqual(len(assigned_raw_moves), 3, "wrong number of reserved raw moves")

        done_finished_move = production.move_finished_ids.filtered(lambda move: move.state == 'done')
        self.assertEqual(len(done_finished_move), 1, "wrong number of done finished moves")
        self.assertEqual(done_finished_move.quantity_done, 1, "finished product are not produced")

        sorted_workorder_ids = backorder.workorder_ids.sorted()
        wo_form = Form(sorted_workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.finished_lot_id = self.sp2
        wo = wo_form.save()
        wo.current_quality_check_id._next()
        wo.record_production()

        wo_form = Form(sorted_workorder_ids[1], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo = wo_form.save()
        wo.current_quality_check_id._next()
        wo.record_production()

        wo_form = Form(sorted_workorder_ids[2], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo = wo_form.save()
        wo.record_production()
        backorder.button_mark_done()
        done_raw_moves = (production | backorder).move_raw_ids.filtered(lambda move: move.state == 'done')
        self.assertEqual(len(done_raw_moves), 6, "wrong number of done raw moves")
        drm_elon = done_raw_moves.filtered(lambda move: move.product_id == self.elon_musk)
        drm_metal = done_raw_moves.filtered(lambda move: move.product_id == self.metal_cylinder)
        drm_child = done_raw_moves.filtered(lambda move: move.product_id == self.trapped_child)
        self.assertEqual(drm_elon[0].quantity_done, 1, "Components are not consumed")
        self.assertEqual(drm_elon[1].quantity_done, 1, "Components are not consumed")
        self.assertEqual(drm_metal[0].quantity_done, 2, "Components are not consumed")
        self.assertEqual(drm_metal[1].quantity_done, 2, "Components are not consumed")
        self.assertEqual(drm_child[0].quantity_done, 12, "Components are not consumed")
        self.assertEqual(drm_child[1].quantity_done, 12, "Components are not consumed")
        done_finished_move = (production | backorder).move_finished_ids.filtered(lambda move: move.state == 'done')
        self.assertEqual(len(done_finished_move), 2, "wrong number of done finished moves")
        self.assertEqual(done_finished_move[0].quantity_done, 1, "finished product are not produced")
        self.assertEqual(done_finished_move[1].quantity_done, 1, "finished product are not produced")

    def test_add_component_2(self):
        """ Adds an extra component when qty_producing is 0 (default value when opening tablet view for a product without tracking).
        Checks that the quantity consumed of the additional component is correct and not doubled as before """
        mrp_order_form = Form(self.env['mrp.production'])

        table = self.env['product.product'].create({
            'name': 'Table',
            'type': 'product',
            'tracking': 'none'})

        table_leg = self.env['product.product'].create({
            'name': 'Table Leg',
            'type': 'product',
            'tracking': 'none'})

        bom_table = self.env['mrp.bom'].create({
            'product_tmpl_id': table.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
            ]})

        self.env['mrp.bom.line'].create({
            'product_id': table_leg.id,
            'product_qty': 2.0,
            'bom_id': bom_table.id,
            'operation_id': bom_table.operation_ids[0].id})

        mrp_order_form.product_id = table
        mrp_order_form.product_qty = 10
        production = mrp_order_form.save()
        production.action_confirm()
        production.workorder_ids[0].button_start()

        # Open tablet view
        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo = wo_form.save()

        # Add an additional product
        additional_form = Form(self.env['mrp_workorder.additional.product'].with_context({
            'default_workorder_id': wo.id,
            'default_type': 'component',
        }))
        additional_form.product_id = self.product_1
        additional_form.product_qty = 6
        additional_wizard = additional_form.save()
        additional_wizard.add_product()

        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 5
        wo = wo_form.save()
        wo.current_quality_check_id._next()
        self.assertEqual(production.move_raw_ids[1].quantity_done, 3)

        # Same test for byproducts
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = table
        mrp_order_form.product_qty = 10
        production = mrp_order_form.save()
        production.action_confirm()
        production.workorder_ids[0].button_start()

        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo = wo_form.save()

        additional_form = Form(self.env['mrp_workorder.additional.product'].with_context({
            'default_workorder_id': wo.id,
            'default_type': 'byproduct',
        }))
        additional_form.product_id = self.product_1
        additional_form.product_qty = 6
        additional_wizard = additional_form.save()
        additional_wizard.add_product()

        wo_form = Form(production.workorder_ids[0], view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 5
        wo = wo_form.save()
        wo.current_quality_check_id._next()
        self.assertEqual(production.move_byproduct_ids[0].quantity_done, 3)

    def test_produce_more_than_planned(self):
        self.env['quality.point'].create({
            'product_ids': [(4, self.submarine_pod.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_submarine.operation_ids[0].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.trapped_child.id,
        })
        self.bom_submarine.bom_line_ids.filtered(lambda line: line.product_id == self.trapped_child).operation_id = self.bom_submarine.operation_ids[0]
        self.submarine_pod.tracking = 'lot'
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.bom_id = self.bom_submarine
        mo_form.product_qty = 1
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()
        sorted_workorder_ids = mo.workorder_ids.sorted()
        wo = sorted_workorder_ids[0]
        wo.button_start()

        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 5
        wo_form.finished_lot_id = self.sp1
        wo = wo_form.save()
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.qty_done, 60, 'The suggested component qty_done is wrong')
        self.assertEqual(qc_form.component_remaining_qty, 60, 'The component remaining quantity is wrong')
        qc = qc_form.save()
        wo.current_quality_check_id._next()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        qc_form.lot_id = self.mc1
        # since lot tracked products are reserved, don't auto multiply amount
        self.assertEqual(qc_form.qty_done, 2, 'The suggested component qty_done is wrong')
        self.assertEqual(qc_form.component_remaining_qty, 10, 'The component remaining quantity is wrong')
        qc = qc_form.save()
        qc._next()
        wo.do_finish()
        self.assertEqual(mo.qty_producing, 5)

    def test_suggested_lot_in_multi_step(self):
        """Suggest the assigned lot in multi step system."""
        self.warehouse = self.env.ref('stock.warehouse0')
        self.env['quality.point'].create({
            'product_ids': [(4, self.submarine_pod.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_submarine.operation_ids[0].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.elon_musk.id,
        })
        self.warehouse.manufacture_steps = 'pbm'
        self.submarine_pod.tracking = 'none'
        self.bom_submarine.bom_line_ids.filtered(lambda l: l.product_id.id != self.elon_musk.id).unlink()
        self.bom_submarine.operation_ids[1:].unlink()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()
        production.action_confirm()
        production.button_plan()

        production.picking_ids.action_assign()
        production.picking_ids.move_line_ids.lot_id = self.elon2
        production.picking_ids.move_line_ids.qty_done = 1
        production.picking_ids.button_validate()

        wo = production.workorder_ids
        wo.button_start()
        self.assertEqual(production.move_raw_ids.move_line_ids.lot_id, self.elon2, "Lot should be assigned.")
        self.assertEqual(wo.lot_id, self.elon2, "Lot should be set in the step")

    def test_step_by_product_variant(self):
        who_attr = self.env['product.attribute'].create({'name': 'Who ?'})
        a1 = self.env['product.attribute.value'].create({'name': 'V0hFCg==', 'attribute_id': who_attr.id})
        a2 = self.env['product.attribute.value'].create({'name': 'QVJN', 'attribute_id': who_attr.id})
        a3 = self.env['product.attribute.value'].create({'name': 'UllW', 'attribute_id': who_attr.id})
        product_who = self.env['product.template'].create({
            'name': 'Odoo staff',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': who_attr.id,
                'value_ids': [(6, 0, [a1.id, a2.id, a3.id])],
            })]
        })
        product_a1 = product_who.product_variant_ids.filtered(lambda v: a1 in v.product_template_attribute_value_ids.product_attribute_value_id)
        product_a2 = product_who.product_variant_ids.filtered(lambda v: a2 in v.product_template_attribute_value_ids.product_attribute_value_id)
        product_a3 = product_who.product_variant_ids.filtered(lambda v: a3 in v.product_template_attribute_value_ids.product_attribute_value_id)

        bom_who = self.env['mrp.bom'].create({
            'code': 'To be ready',
            'product_tmpl_id': product_who.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.trapped_child.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'name': 'Be ready', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 60, 'sequence': 1}),
            ]
        })

        p1 = self.env['quality.point'].create({
            'product_ids': [(4, product_a1.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': bom_who.operation_ids[0].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
            'note': 'Installing VIM (pcs xi ipzth adi du ixbt)',
        })
        p2 = self.env['quality.point'].create({
            'product_ids': [(4, product_a2.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': bom_who.operation_ids[0].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
            'note': 'Taking lot of coffee with UElN',
        })

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = product_a1
        production_a1 = mrp_order_form.save()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = product_a2
        production_a2 = mrp_order_form.save()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = product_a3
        production_a3 = mrp_order_form.save()

        self.assertEqual(production_a1.bom_id, bom_who)
        self.assertEqual(production_a2.bom_id, bom_who)
        self.assertEqual(production_a3.bom_id, bom_who)

        production_a1.action_confirm()
        (production_a2 | production_a3).action_confirm()

        self.assertEqual(len(production_a1.workorder_ids.check_ids), 1)
        self.assertEqual(production_a1.workorder_ids.check_ids.point_id, p1)
        self.assertEqual(len(production_a2.workorder_ids.check_ids), 1)
        self.assertEqual(production_a2.workorder_ids.check_ids.point_id, p2)
        self.assertEqual(len(production_a3.workorder_ids.check_ids), 0)

    def test_add_workorder_into_a_backorder(self):
        """ Checks a new workorder can be created and processed into a backorder."""
        (self.submarine_pod | self.elon_musk | self.metal_cylinder).tracking = 'none'
        self.bom_submarine.consumption = 'flexible'

        def process_workorder(workorders, qty, next_and_finish=False):
            for wo in workorders:
                wo.button_start()
                wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
                wo_form.qty_producing = qty
                wo = wo_form.save()
                if next_and_finish:
                    if wo.current_quality_check_id:
                        wo.current_quality_check_id._next()
                    wo.do_finish()
                elif wo.current_quality_check_id:
                    wo.current_quality_check_id.action_continue()

        # Creates a MO with 2 WO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()

        # Processes partially the workorders.
        process_workorder(mo.workorder_ids.sorted(), 2)

        # Marks the MO as done and creates a backorder.
        action = mo.button_mark_done()
        backorder_form = Form(self.env[action['res_model']].with_context(**action['context']))
        backorder_form.save().action_backorder()

        backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo.state, 'done')
        self.assertEqual(backorder.state, 'confirmed')
        self.assertEqual(len(backorder.workorder_ids), 3)
        self.assertEqual(backorder.workorder_ids.mapped('qty_production'), [8.0, 8.0, 8.0])

        # Adds a new WO in the backorder.
        mo_form = Form(backorder)
        with mo_form.workorder_ids.new() as wo_line:
            wo_line.name = "OP-SP"
            wo_line.workcenter_id = self.workcenter_1
        mo_form.save()

        # Again, processes partially the workorders.
        process_workorder(backorder.workorder_ids.sorted(), 5, True)

    def test_operations_with_test_type_register_consumed_materials(self):
        """ Production with a strict consumption
        Check that operation must contain related consumption material"""

        # create operation
        operation1 = self.env['mrp.routing.workcenter'].create({
            'name': 'Operation1',
            'bom_id': self.bom_2.id,
            'workcenter_id': self.workcenter_2.id,
        })
        operation2 = self.env['mrp.routing.workcenter'].create({
            'name': 'Operation2',
            'bom_id': self.bom_2.id,
            'workcenter_id': self.workcenter_2.id,
        })

        # update operations in bom
        self.bom_2.write({'operation_ids': [(6, 0, [operation1.id, operation2.id])]})

        # create quality point
        self.env['quality.point'].create({
            'product_ids': [(6, 0, self.product_5.ids)],
            'picking_type_ids': [(6, 0, self.bom_2.picking_type_id.ids)],
            'operation_id': operation1.id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.product_3.id,
        })
        # update quantities
        self.env['stock.quant']._update_available_quantity(self.product_3, self.location_1, 20.0)
        self.env['stock.quant']._update_available_quantity(self.product_4, self.location_1, 20.0)

        # create a mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_5
        mo_form.bom_id = self.bom_2
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        wo = mo.workorder_ids[0]
        wo.button_start()
        wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
        wo_form.qty_producing = 3
        wo = wo_form.save()
        self.assertEqual(len(wo.check_ids), 1, "their should be 1 quality check")
        qc_form = Form(wo.current_quality_check_id, view='mrp_workorder.quality_check_view_form_tablet')
        self.assertEqual(qc_form.component_id, self.product_3, 'operation must contain related consumption material')
