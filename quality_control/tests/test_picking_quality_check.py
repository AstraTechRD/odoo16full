# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_common import TestQualityCommon

class TestQualityCheck(TestQualityCommon):

    def test_00_picking_quality_check(self):

        """Test quality check on incoming shipment."""

        # Create Quality Point for incoming shipment.
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
        })

        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "First Quality Point not created for Laptop Customized.")

        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Confirm incoming shipment.
        self.picking_in.action_confirm()

        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # 'Pass' Quality Checks of incoming shipment.
        self.picking_in.check_ids.do_pass()

        # Validate incoming shipment.
        self.picking_in.button_validate()

        # Now check state of quality check.
        self.assertEqual(self.picking_in.check_ids.quality_state, 'pass')

    def test_01_picking_quality_check_type_text(self):

        """ Test a Quality Check on a picking with 'Instruction'
        as test type.
        """
        # Create Quality Point for incoming shipment with 'Instructions' as test type
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality.test_type_instructions').id
        })

        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "Quality Point not created")

        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Confirm incoming shipment.
        self.picking_in.action_confirm()

        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # Check that the Quality Check on the picking has 'instruction' as test_type
        self.assertEqual(self.picking_in.check_ids[0].test_type, 'instructions')

    def test_02_picking_quality_check_type_picture(self):

        """ Test a Quality Check on a picking with 'Take Picture'
        as test type.
        """
        # Create Quality Point for incoming shipment with 'Take Picture' as test type
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality.test_type_picture').id
        })
        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "Quality Point not created")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # Check that the Quality Check on the picking has 'picture' as test_type
        self.assertEqual(self.picking_in.check_ids[0].test_type, 'picture')

    def test_03_lot_quality_check(self):
        """ Test a Quality Check at the lot level.
        """
        product_tracked_by_lot = self.env['product.product'].create({
            'name': 'Product tracked by lot',
            'tracking': 'lot',
        })

        product = self.env['product.product'].create({
            'name': 'Product',
            'tracking': 'none',
        })

        # Create Quality Point for incoming shipment on lots with 'Measure' as test type
        self.quality_point_test1 = self.env['quality.point'].create({
            'product_ids': [product_tracked_by_lot.id],
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'is_lot_tested_fractionally': True,
            'testing_percentage_within_lot': 10.02,
            'measure_on': 'move_line',
            'norm': 5.,
            'tolerance_min': 4.,
            'tolerance_max': 6.,
        })

        # Create Quality Point for incoming shipment on lots for all products
        self.quality_point_test2 = self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })

        # Create Quality Point for product without tracking
        self.quality_point_test3 = self.env['quality.point'].create({
            'product_ids': [product.id],
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })

        # Check that the quality points are created
        self.assertTrue(self.quality_point_test1, "Quality Point not created")
        self.assertTrue(self.quality_point_test2, "Quality Point not created")
        self.assertTrue(self.quality_point_test3, "Quality Point not created")

        # Create incoming shipment
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })

        move = self.env['stock.move'].create({
            'name': product_tracked_by_lot.name,
            'product_id': product_tracked_by_lot.id,
            'product_uom_qty': 11,
            'product_uom': product_tracked_by_lot.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Creating move lines with the serial number widget
        move.next_serial = "1"
        move._generate_serial_numbers(next_serial_count=10)
        self.assertTrue(len(move.move_line_ids) == 10, "Not all move lines are created with _generate_serial_number")

        # Check that quality checks were created
        self.assertTrue(len(move.move_line_ids.check_ids) == 20, "Wrong number of Quality Checks created on the move lines")

        # Create move line without qty_done and setting it after
        move_line_vals = move._prepare_move_line_vals()
        move_line = self.env['stock.move.line'].create(move_line_vals)
        move_line.qty_done = 1.
        self.assertTrue(len(move.move_line_ids.check_ids) == 22, "Wrong number of Quality Checks created on the move lines")

        # Updating quantity of one move line
        move.move_line_ids[0].qty_done = 2
        check_line1 = move.move_line_ids[0].check_ids[0]
        check_line2 = move.move_line_ids[1].check_ids[0]

        # Check that the percentage of the lot to check is correct
        self.assertTrue(check_line1.qty_to_test == 0.21, "Quantity to test within lot not well calculated (check rounding)")
        self.assertTrue(check_line2.qty_to_test == 0.11, "Quantity to test within lot not well calculated (check rounding)")

        # Check that tests are failing and succeeding properly
        check_line1.measure = 3.
        check_line2.measure = 4.5
        check_line1.do_measure()
        check_line2.do_measure()
        self.assertTrue(check_line1.quality_state == 'fail', "Quality Check of type 'measure' not failing on move line")
        self.assertTrue(check_line2.quality_state == 'pass', "Quality Check of type 'measure' not passing on move line")

        # Create move with a product without tracking with done quantity
        move_without_tracking1 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'quantity_done': 1,
            'product_uom': product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        self.assertTrue(len(move_without_tracking1.move_line_ids.check_ids) == 2, "Wrong number of Quality Checks created on the move lines")

        # Create move with a product without tracking without done quantity and changing done quantity after
        move_without_tracking2 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'quantity_done': 0,
            'product_uom': product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        move_without_tracking2.quantity_done = 1
        self.assertTrue(len(move_without_tracking2.move_line_ids.check_ids) == 2, "Wrong number of Quality Checks created on the move lines")

    def test_04_picking_quality_check_creation_no_products_no_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with no products and no product_categories set
        """
        # Create Quality Point for incoming shipment with no product or product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that Quality Check for incoming shipment has been created.
        self.assertEqual(len(self.picking_in.check_ids), 1)

    def test_05_picking_quality_check_creation_with_product_no_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with products and no product_categories set
        """
        # Create Quality Point for incoming shipment with only a product set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product.
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that only one Quality Check for incoming shipment has been created for the right product.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 0)

    def test_06_picking_quality_check_creation_no_product_with_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with no products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with product having right category (child of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with product having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that only one Quality Check for incoming shipment has been created for the right category.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 0)

    def test_07_picking_quality_check_creation_with_product_and_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with both products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product_2.id), (4, self.product_4.id)],
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product but having right category (child of Quality Point set category.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product but having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product and having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product having right category
        self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that Quality Check for incoming shipment have been created only for the right product / category.
        self.assertEqual(len(self.picking_in.check_ids), 3)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_3.id)), 0)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_4.id)), 1)

    def test_08_on_product_creation_with_product_and_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with both products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product_2.id), (4, self.product_4.id)],
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product but having right category (child of Quality Point set category.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product but having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product and having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product having right category
        self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        for line in self.picking_in.move_line_ids:
            line.qty_done = line.reserved_qty
        # Check that Quality Check for incoming shipment have been created for all the good move lines
        self.assertEqual(len(self.picking_in.check_ids), 3)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_3.id)), 0)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_4.id)), 1)

    def test_09_quality_check_on_operations(self):

        """ Test Quality Check creation of 'operation' type, meaning only one QC will be created per picking.
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        quality_point_operation_type = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'operation',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        } for product in (self.product, self.product_2)])
        receipt.action_confirm()

        self.assertEqual(len(receipt.check_ids), 1)
        self.assertEqual(receipt.check_ids.point_id, quality_point_operation_type)
        self.assertEqual(receipt.check_ids.picking_id, receipt)

    def test_checks_removal_on_SM_cancellation(self):
        """
        Configuration:
            - 2 storable products P1 and P2
            - Receipt in 2 steps
            - QCP for internal pickings
        Process a first receipt with P1 and P2 (an internal picking and two
        quality checks are created)
        Process a second receipt with P1. The SM input->stock should be merged
        into the existing one and the quality checks should still exist
        """
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.reception_steps = 'two_steps'

        p01, p02 = self.env['product.product'].create([{
            'name': name,
            'type': 'product',
        } for name in ('SuperProduct01', 'SuperProduct02')])

        self.env['quality.point'].create([{
            'product_ids': [(4, product.id)],
            'picking_type_ids': [(4, warehouse.int_type_id.id)],
        } for product in (p01, p02)])

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        } for product in (p01, p02)])
        receipt.action_confirm()
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        internal_transfer = self.env['stock.picking'].search(
            [('location_id', '=', warehouse.wh_input_stock_loc_id.id), ('picking_type_id', '=', warehouse.int_type_id.id)],
            order='id desc', limit=1)
        self.assertEqual(internal_transfer.check_ids.product_id, p01 + p02)

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create({
            'name': p01.name,
            'product_id': p01.id,
            'product_uom_qty': 1,
            'product_uom': p01.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        receipt.action_confirm()
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        self.assertRecordValues(internal_transfer.move_ids, [
            {'product_id': p01.id, 'product_uom_qty': 2},
            {'product_id': p02.id, 'product_uom_qty': 1},
        ])
        self.assertEqual(internal_transfer.check_ids.product_id, p01 + p02)
