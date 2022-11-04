# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged, Form


@tagged('-standard', 'external')
class TestDeliveryUPS(TransactionCase):

    def setUp(self):
        super(TestDeliveryUPS, self).setUp()

        self.iPadMini = self.env.ref('product.product_product_6')
        self.large_desk = self.env.ref('product.product_product_8')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Add a full address to "Your Company" and "Agrolait"
        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({'country_id': self.env.ref('base.us').id,
                                 'state_id': self.env.ref('base.state_us_5').id,
                                 'city': 'San Francisco',
                                 'street': '51 Federal Street',
                                 'zip': '94107'})
        self.agrolait = self.env.ref('base.res_partner_2')
        self.agrolait.write({'country_id': self.env.ref('base.be').id,
                             'city': 'Auderghem-Ouderghem',
                             'street': 'Avenue Edmond Van Nieuwenhuyse',
                             'zip': '1160'})
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')

    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method.
        """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'delivery_package_type_id': picking.carrier_id.ups_default_package_type_id.id
        })
        wiz.action_put_in_pack()

    def test_01_ups_basic_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        # Set service type = 'UPS Worldwide Expedited', which is available between US to BE
        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_service_type': '08',
                       'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '3',
                                                   'width': '3',
                                                   'packaging_length': '3'})

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "UPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity_done = 1.0
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "UPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "UPS carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_02_ups_multipackage_flow(self):
        SaleOrder = self.env['sale.order']

        # Set package type = 'Pallet' and service type = 'UPS Worldwide Express Freight'
        # so in this case height, width and length required.
        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_package_type_id': self.env.ref('delivery_ups.ups_packaging_30').id,
                       'ups_default_service_type': '96',
                       'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '3',
                                                   'width': '3',
                                                   'packaging_length': '3'})

        sol_1_vals = {'product_id': self.iPadMini.id,
                      'name': "[A1232] Large Cabinet",
                      'product_uom': self.uom_unit.id,
                      'product_uom_qty': 1.0,
                      'price_unit': self.iPadMini.lst_price}

        sol_2_vals = {'product_id': self.large_desk.id,
                      'name': "[A1090] Large Desk",
                      'product_uom': self.uom_unit.id,
                      'product_uom_qty': 1.0,
                      'price_unit': self.large_desk.lst_price}

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "UPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        move0 = picking.move_ids[0]
        move0.quantity_done = 1.0
        self.wiz_put_in_pack(picking)
        move1 = picking.move_ids[1]
        move1.quantity_done = 1.0
        self.wiz_put_in_pack(picking)
        self.assertEqual(len(picking.move_line_ids.mapped('result_package_id')), 2, "2 packages should have been created at this point")
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "UPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "UPS carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_03_ups_flow_from_delivery_order(self):
        # Set service type = 'UPS Worldwide Expedited', which is available between US to BE
        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_service_type': '08',
                       'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '3',
                                                   'width': '3',
                                                   'packaging_length': '3'})

        StockPicking = self.env['stock.picking']

        order1_vals = {
                    'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id}

        do_vals = { 'partner_id': self.agrolait.id,
                    'carrier_id': carrier.id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'move_ids_without_package': [(0, None, order1_vals)]}

        delivery_order = StockPicking.create(do_vals)
        self.assertEqual(delivery_order.state, 'draft', 'Shipment state should be draft.')

        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'confirmed', 'Shipment state should be waiting(confirmed).')

        delivery_order.action_assign()
        self.assertEqual(delivery_order.state, 'assigned', 'Shipment state should be ready(assigned).')
        delivery_order.move_ids_without_package.quantity_done = 1.0

        delivery_order.button_validate()
        self.assertEqual(delivery_order.state, 'done', 'Shipment state should be done.')

    def test_04_backorder_and_track_number(self):
        """ Suppose a two-steps delivery with 2 x Product A and 2 x Product B.
        For the Pick step, process a first picking (PICK01) with 2 x Product A
        and a backorder (PICK02) with 2 x Product B
        For the Out step, process a first picking (OUT01) with 1 x Product A
        and a backorder (OUT02) with 1 x Product A and 2 x Product B
        This test ensures that:
            - OUT01 and OUT02 have their own tracking reference
            - The tracking reference of PICK01 is defined with the one of OUT01 and OUT02
            - The tracking reference of PICK02 is defined with the one of OUT02
        """
        def process_picking(picking):
            action = picking.button_validate()
            wizard = Form(self.env[action['res_model']].with_context(action['context']))
            wizard.save().process()

        warehouse = self.env['sale.order']._default_warehouse_id()
        warehouse.delivery_steps = 'pick_ship'
        stock_location = warehouse.lot_stock_id

        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_service_type': '08', 'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '1', 'width': '1', 'packaging_length': '1'})

        product_a, product_b = self.env['product.product'].create([{
            'name': p_name,
            'weight': 1,
        } for p_name in ['Product A', 'Product B']])

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.agrolait
        with so_form.order_line.new() as line:
            line.product_id = product_a
            line.product_uom_qty = 2
        with so_form.order_line.new() as line:
            line.product_id = product_b
            line.product_uom_qty = 2
        so = so_form.save()

        # Add UPS shipping
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        choose_delivery_carrier.button_confirm()

        so.action_confirm()
        pick01 = so.picking_ids.filtered(lambda p: p.location_id == stock_location)
        out01 = so.picking_ids - pick01

        # First step with 2 x Product A
        pick01.move_ids.filtered(lambda m: m.product_id == product_a).quantity_done = 2
        process_picking(pick01)
        # First step with 2 x Product B
        pick02 = pick01.backorder_ids
        process_picking(pick02)

        # Second step with 1 x Product A
        out01.move_ids.filtered(lambda m: m.product_id == product_a).quantity_done = 1
        process_picking(out01)
        out02 = out01.backorder_ids
        self.assertTrue(out01.carrier_tracking_ref)
        self.assertFalse(out02.carrier_tracking_ref)
        self.assertEqual(pick01.carrier_tracking_ref, out01.carrier_tracking_ref)
        self.assertFalse(pick02.carrier_tracking_ref)

        # Second step with 1 x Product A + 2 x Product B
        process_picking(out02)
        self.assertTrue(out01.carrier_tracking_ref)
        self.assertTrue(out02.carrier_tracking_ref)
        self.assertNotEqual(out01.carrier_tracking_ref, out02.carrier_tracking_ref)
        self.assertEqual(pick01.carrier_tracking_ref, out01.carrier_tracking_ref + ',' + out02.carrier_tracking_ref)
        self.assertEqual(pick02.carrier_tracking_ref, out02.carrier_tracking_ref)
