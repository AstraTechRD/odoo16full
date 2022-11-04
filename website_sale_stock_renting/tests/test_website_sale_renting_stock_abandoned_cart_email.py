# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.website_sale_stock.tests.test_website_sale_stock_abandoned_cart_email import TestWebsiteSaleCartAbandonedCommon
from odoo.tests.common import tagged

@tagged('post_install', '-at_install')

class TestWebsiteSaleStockRentingAbandonedCartEmail(TestWebsiteSaleCartAbandonedCommon):
    def test_website_sale_stock_renting_abandoned_cart_email(self):
        """Make sure the send_abandoned_cart_email method sends the correct emails."""

        website = self.env['website'].get_current_website()
        website.send_abandoned_cart_email = True

        renting_product_template = self.env['product.template'].create({
            'name': 'renting_product_template',
            'type': 'product',
            'rent_ok': True,
            'allow_out_of_stock_order': False
        })
        renting_product_product = self.env['product.product'].create({
            'name': 'renting_product_product',
            'product_tmpl_id': renting_product_template.id,
        })
        order_line = [[0, 0, {
            'product_id': renting_product_product.id,
            'product_uom_qty': 1,
            'start_date': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'return_date': datetime.utcnow() + relativedelta(days=1),
            'is_rental': True,
        }]]
        customer = self.env['res.partner'].create({
            'name': 'a',
            'email': 'a@example.com',
        })
        abandoned_sale_order_with_not_available_rental = self.env['sale.order'].create({
            'partner_id': customer.id,
            'website_id': website.id,
            'state': 'draft',
            'date_order': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'order_line': order_line
        })

        self.assertFalse(self.send_mail_patched(abandoned_sale_order_with_not_available_rental.id))
        # Reset cart_recovery sent state
        abandoned_sale_order_with_not_available_rental.cart_recovery_email_sent = False


        # Replenish the stock of the product
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': renting_product_product.id,
            'inventory_quantity': 1.0,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
        }).action_apply_inventory()

        self.assertTrue(self.send_mail_patched(abandoned_sale_order_with_not_available_rental.id))

        # Test if the email is not sent if the rental is not available anymore

        order_line = [[0, 0, {
            'product_id': renting_product_product.id,
            'product_uom_qty': 1,
            'start_date': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'return_date': datetime.utcnow() + relativedelta(days=1),
            'is_rental': True,
        }]]

        sale_order = self.env['sale.order'].create({
            'partner_id': customer.id,
            'website_id': website.id,
            'state': 'draft',
            'date_order': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'order_line': order_line
        })
        sale_order.state = 'sale'
        order_line = [[0, 0, {
            'product_id': renting_product_product.id,
            'product_uom_qty': 1,
            'start_date': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'return_date': datetime.utcnow() + relativedelta(days=1),
            'is_rental': True,
        }]]

        sale_order2 = self.env['sale.order'].create({
            'partner_id': customer.id,
            'website_id': website.id,
            'state': 'draft',
            'date_order': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'order_line': order_line
        })

        self.assertFalse(self.send_mail_patched(sale_order2.id))
