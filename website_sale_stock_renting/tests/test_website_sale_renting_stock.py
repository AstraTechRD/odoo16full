# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon

@tagged('post_install', '-at_install')
class TestWebsiteSaleStockRenting(TestWebsiteSaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.computer.type = 'product'
        cls.computer.allow_out_of_stock_order = False

        cls.company.update({
            'renting_forbidden_sat': False,
            'renting_forbidden_sun': False,
        })

        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        quants = cls.env['stock.quant'].create({
            'product_id': cls.computer.id,
            'inventory_quantity': 5.0,
            'location_id': cls.wh.lot_stock_id.id
        })
        quants.action_apply_inventory()
        cls.so = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
            'warehouse_id': cls.wh.id,
        })
        cls.now = fields.Datetime.now()
        cls.sol = cls.env['sale.order.line'].create({
            'order_id': cls.so.id,
            'product_id': cls.computer.id,
            'start_date': cls.now + relativedelta(days=1),
            'return_date': cls.now + relativedelta(days=3),
            'is_rental': True,
            'product_uom_qty': 3,
        })
        cls.current_website = cls.env['website'].get_current_website()

    def test_sol_draft(self):
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {}
        expected_key_dates = [from_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (no rental)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 1, "Availabilities should only have one entry")
        expected_availability = {'start': from_date, 'end': to_date, 'quantity_available': 5}
        self.assertDictEqual(availabilities[0], expected_availability, "Availabilities should be equal to the expected dict (all quantity available)")

        cart_qty, free_qty = self.so._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 3, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 5, "Free quantity should be equal to 5 (all products)")

    def test_sol_sent(self):
        self.so.action_quotation_sent()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {self.sol.start_date: 3, self.sol.return_date: -3}
        expected_key_dates = [from_date, self.sol.start_date, self.sol.return_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (a rental)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 3, "Availabilities should only have three entries")
        expected_availability = {'start': self.sol.start_date, 'end': self.sol.return_date, 'quantity_available': 2}
        self.assertDictEqual(availabilities[1], expected_availability, "Availabilities should be equal to the expected dict (only 2 available)")

        cart_qty, free_qty = self.so._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 3, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 5, "Free quantity should be equal to 5 (all products)")

    def test_sol_confirmed(self):
        self.so.action_confirm()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {self.sol.start_date: 3, self.sol.return_date: -3}
        expected_key_dates = [from_date, self.sol.start_date, self.sol.return_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (3 products rented)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 3, "Availabilities should only have three entries")
        expected_availability = {'start': self.sol.start_date, 'end': self.sol.return_date, 'quantity_available': 2}
        self.assertDictEqual(availabilities[1], expected_availability, "Availabilities should be equal to the expected dict (only 2 available)")

        cart_qty, free_qty = self.so._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 3, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 5, "Free quantity should be equal to 5 (all products)")

    def test_sol_pickup(self):
        self.so.action_confirm()
        pickup_action = self.so.open_pickup()
        wizard = self.env['rental.order.wizard'].with_context(pickup_action['context']).create({})
        with freeze_time(self.sol.start_date):
            wizard.apply()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {self.sol.start_date: 3, self.sol.return_date: -3}
        expected_key_dates = [from_date, self.sol.start_date, self.sol.return_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (3 products rented)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 3, "Availabilities should only have three entries")
        expected_availability = {'start': self.sol.start_date, 'end': self.sol.return_date, 'quantity_available': 2}
        self.assertDictEqual(availabilities[1], expected_availability, "Availabilities should be equal to the expected dict (only 2 available)")

        cart_qty, free_qty = self.so._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 3, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 5, "Free quantity should be equal to 5 (all products)")

    def test_sol_return(self):
        self.so.action_confirm()
        pickup_action = self.so.open_pickup()
        wizard = self.env['rental.order.wizard'].with_context(pickup_action['context']).create({})
        with freeze_time(self.sol.start_date):
            wizard.apply()
        return_action = self.so.open_return()
        wizard = self.env['rental.order.wizard'].with_context(return_action['context']).create({})
        with freeze_time(self.sol.return_date):
            wizard.apply()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {self.sol.start_date: 3, self.sol.return_date: -3,}
        expected_key_dates = [from_date, self.sol.start_date, self.sol.return_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (3 products rented)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 3, "Availabilities should only have three entries")
        expected_availability = {'start': self.sol.start_date, 'end': self.sol.return_date, 'quantity_available': 2}
        self.assertDictEqual(availabilities[1], expected_availability, "Availabilities should be equal to the expected dict (only 2 available)")

        cart_qty, free_qty = self.so._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 3, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 5, "Free quantity should be equal to 5 (all products)")

    def test_multiple_sol(self):
        self.so.action_confirm()
        so2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'warehouse_id': self.wh.id,
        })
        sol2 = self.env['sale.order.line'].create({
            'order_id': so2.id,
            'product_id': self.computer.id,
            'start_date': self.now + relativedelta(days=1),
            'return_date': self.now + relativedelta(days=2),
            'is_rental': True,
            'product_uom_qty': 2,
        })
        so2.action_confirm()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {self.sol.start_date: 5, sol2.return_date: -2, self.sol.return_date: -3}
        expected_key_dates = [from_date, self.sol.start_date, sol2.return_date, self.sol.return_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (3 products rented)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 4, "Availabilities should only have four entries")
        expected_availability = {'start': self.sol.start_date, 'end': sol2.return_date, 'quantity_available': 0}
        self.assertDictEqual(availabilities[1], expected_availability, "Availabilities should be equal to the expected dict (out of stock)")
        expected_availability = {'start': sol2.return_date, 'end': self.sol.return_date, 'quantity_available': 2}
        self.assertDictEqual(availabilities[2], expected_availability, "Availabilities should be equal to the expected dict (only 2 available)")

        cart_qty, free_qty = so2._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 2, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 2, "Free quantity should be equal to 5 minus sol product qty (3)")


    def test_multiple_sol_with_first_one_picked_up(self):
        self.so.action_confirm()
        pickup_action = self.so.open_pickup()
        wizard = self.env['rental.order.wizard'].with_context(pickup_action['context']).create({})
        with freeze_time(self.sol.start_date):
            wizard.apply()
        so2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'warehouse_id': self.wh.id,
        })
        sol2 = self.env['sale.order.line'].create({
            'order_id': so2.id,
            'product_id': self.computer.id,
            'start_date': self.now + relativedelta(days=1),
            'return_date': self.now + relativedelta(days=2),
            'is_rental': True,
            'product_uom_qty': 2,
        })
        so2.action_confirm()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        expected_rented_quantities = {self.sol.start_date: 5, sol2.return_date: -2, self.sol.return_date: -3}
        expected_key_dates = [from_date, self.sol.start_date, sol2.return_date, self.sol.return_date, to_date]
        self.assertDictEqual(rented_quantities, expected_rented_quantities, "Rented quantities should contain the expected values (3 products rented)")
        self.assertListEqual(key_dates, expected_key_dates, "Key dates should contain the expected dates sorted.")
        availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertEqual(len(availabilities), 4, "Availabilities should only have four entries")
        expected_availability = {'start': self.sol.start_date, 'end': sol2.return_date, 'quantity_available': 0}
        self.assertDictEqual(availabilities[1], expected_availability, "Availabilities should be equal to the expected dict (out of stock)")
        expected_availability = {'start': sol2.return_date, 'end': self.sol.return_date, 'quantity_available': 2}
        self.assertDictEqual(availabilities[2], expected_availability, "Availabilities should be equal to the expected dict (only 2 available)")

        cart_qty, free_qty = so2._get_cart_and_free_qty(product=self.computer, start_date=from_date, end_date=to_date)
        self.assertEqual(cart_qty, 2, "Cart quantity should be equal to sol2 product qty")
        self.assertEqual(free_qty, 2, "Free quantity should be equal to 5 minus picked up product qty (3)")

    def test_cart_update_max_quantity(self):
        with MockRequest(self.env, website=self.current_website, sale_order_id=self.so.id):
            website_so = self.current_website.sale_get_order()
            values = website_so._cart_update(
                product_id=self.computer.id, line_id=self.sol.id, add_qty=3,
                start_date=self.now + relativedelta(days=1),
                end_date=self.now + relativedelta(days=3)
            )
            self.assertTrue(values.get('warning', False))
            self.assertEqual(values.get('quantity'), 5)

    def test_cart_update_no_more_available(self):
        self.sol.product_uom_qty = 5

        with MockRequest(self.env, website=self.current_website, sale_order_id=self.so.id):
            website_so = self.current_website.sale_get_order()
            values = website_so._cart_update(
                product_id=self.computer.id, add_qty=5,
                start_date=self.now + relativedelta(days=2),
                end_date=self.now + relativedelta(days=5)
            )
            self.assertTrue(values.get('warning', False))
            self.assertEqual(values.get('quantity'), 0)
