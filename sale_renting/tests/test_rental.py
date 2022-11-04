# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tools import float_compare
from odoo.tests import HttpCase, tagged, TransactionCase


class TestRentalCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_id = cls.env['product.product'].create({
            'name': 'Projector',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'type': 'consu',
            'rent_ok': True,
            'extra_hourly': 7.0,
            'extra_daily': 30.0,
        })

        cls.product_template_id = cls.product_id.product_tmpl_id

        cls.product_template_id.product_pricing_ids.unlink()
        cls.recurrence_hourly = cls.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        cls.recurrence_5_hours = cls.env['sale.temporal.recurrence'].create({'duration': 5.0, 'unit': 'hour'})
        cls.recurrence_15_hours = cls.env['sale.temporal.recurrence'].create({'duration': 15.0, 'unit': 'hour'})
        cls.recurrence_daily = cls.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'day'})
        # blank the demo pricings

        PRICINGS = [
            {
                'recurrence_id': cls.recurrence_hourly.id,
                'price': 3.5,
            }, {
                'recurrence_id': cls.recurrence_5_hours.id,
                'price': 15.0,
            }, {
                'recurrence_id': cls.recurrence_15_hours.id,
                'price': 40.0,
            }, {
                'recurrence_id': cls.recurrence_daily.id,
                'price': 60.0,
            },
        ]

        for pricing in PRICINGS:
            pricing.update(product_template_id=cls.product_template_id.id)
            cls.env['product.pricing'].create(pricing)

        cls.tax_included = cls.env['account.tax'].create({'name': 'Tax Incl', 'amount': 10, 'price_include': True})
        cls.tax_excluded = cls.env['account.tax'].create({'name': 'Tax Excl', 'amount': 10, 'price_include': False})

    def test_pricing(self):
        # check pricing returned = expected
        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=9.0, unit='hour')._compute_price(9.0, 'hour'),
            30.0
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=11.0, unit='hour')._compute_price(11.0, 'hour'),
            38.5
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=16.0, unit='hour')._compute_price(16.0, 'hour'),
            56.0
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=20, unit='hour')._compute_price(20.0, 'hour'),
            60.0
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(duration=24.0, unit='hour')._compute_price(24.0, 'hour'),
            60.0
        )

    def test_pricing_advanced(self):
        # with pricings applied only to some variants ...
        return

    def test_pricelists(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        pricelist_B = self.env['product.pricelist'].create({
            'name': 'Pricelist B',
        })

        PRICINGS = [
            {
                'recurrence_id': self.recurrence_hourly.id,
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }, {
                'recurrence_id': self.recurrence_5_hours.id,
                'price': 15.0,
                'pricelist_id': pricelist_B.id,
            }
        ]
        self.product_template_id.list_price = 42
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })

        reservation_begin = fields.Datetime.now()
        pickup_date = reservation_begin + relativedelta(days=1)
        return_date = pickup_date + relativedelta(hours=1)

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
            'reservation_begin': reservation_begin,
            'start_date': pickup_date,
            'return_date': return_date,
            'is_rental': True,
        })

        sale_order.write({'pricelist_id': pricelist_A.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 3.5, "Pricing should take into account pricelist A")
        sale_order.write({'pricelist_id': pricelist_B.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 15, "Pricing should take into account pricelist B")

    def test_delay_pricing(self):
        # Return Products late and verify duration is correct.
        self.product_id.extra_hourly = 2.5
        self.product_id.extra_daily = 15.0

        self.assertEqual(
            self.product_id._compute_delay_price(timedelta(hours=5.0)),
            12.5
        )

        self.assertEqual(
            self.product_id._compute_delay_price(timedelta(hours=5.0, days=6)),
            102.5
        )

    def test_discount(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
            'discount_policy': 'without_discount',
            'company_id': self.env.company.id,
            'item_ids': [(0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 10,
            })],
        })
        pricelist_B = self.env['product.pricelist'].create({
            'name': 'Pricelist B',
            'discount_policy': 'without_discount',
            'company_id': self.env.company.id,
            'item_ids': [(0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 20,
            })],
        })

        PRICINGS = [
            {
                'recurrence_id': self.recurrence_hourly.id,
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }, {
                'recurrence_id': self.recurrence_5_hours.id,
                'price': 15.0,
                'pricelist_id': pricelist_B.id,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })

        reservation_begin = fields.Datetime.now()
        pickup_date = reservation_begin + relativedelta(days=1)
        return_date = pickup_date + relativedelta(hours=1)

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': 1,
            'order_id': sale_order.id,
            'reservation_begin': reservation_begin,
            'start_date': pickup_date,
            'return_date': return_date,
            'is_rental': True,
            'price_unit': 1
        })
        sale_order.write({'pricelist_id': pricelist_A.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.discount, 0, "Discount should always been 0 on pricelist change")
        sale_order.write({'pricelist_id': pricelist_B.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.discount, 0, "Discount should always been 0 on pricelist change")

    def test_is_add_to_cart_possible(self):
        # Check that `is_add_to_cart_possible` returns True when
        # the product is active and can be rent or/and sold
        self.product_template_id.write({'sale_ok': False, 'rent_ok': False})
        self.assertFalse(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'sale_ok': True})
        self.assertTrue(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'sale_ok': False, 'rent_ok': True})
        self.assertTrue(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'sale_ok': True})
        self.assertTrue(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'active': False})
        self.assertFalse(self.product_template_id._is_add_to_cart_possible())

    # TODO availability testing with sale_rental functions? (no stock)

    def test_no_pickup_nor_return(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})

        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(sol.price_unit, 1, "No pricing should be taken into account if no pickup nor return date.")
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 1, "Update price should not alter first computed price.")

    def test_no_price_update_on_pickup_return_update(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})

        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(sol.price_unit, 1, "No pricing should be taken into account if no pickup nor return date.")
        sol.write({
            'start_date': fields.Datetime.now() + relativedelta(days=1),
            'return_date': fields.Datetime.now() + relativedelta(days=1, hours=1),
            'is_rental': True,
        })
        self.assertEqual(sol.price_unit, 1, "Update price should not alter first computed price.")
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 3.5, "Update price should not alter first computed price.")

    def test_no_pricing_for_pricelist(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
            'start_date': fields.Datetime.now() + relativedelta(days=1),
            'return_date': fields.Datetime.now() + relativedelta(days=1, hours=1),
            'is_rental': True,
        })

        self.assertEqual(sol.price_unit, 1, "No pricing should be taken into account if no pricing corresponds to a given pricelist.")

    def test_contextual_price_is_pickup_return_dependant(self):
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        price = self.product_template_id.with_context(
            start_date=fields.Datetime.now() + relativedelta(days=1),
            end_date=fields.Datetime.now() + relativedelta(days=1, hours=2),
            pricelist=pricelist_A.id
        )._get_contextual_price()
        self.assertEqual(price, 7, "Contextual price should take pickup and return date into account")

    def test_renting_taxes_inc2ex(self):

        fiscal_position_inc2ex = self.env['account.fiscal.position'].create({'name': 'inc2ex'})
        self.env['account.fiscal.position.tax'].create({
            'position_id': fiscal_position_inc2ex.id,
            'tax_src_id': self.tax_included.id,
            'tax_dest_id': self.tax_excluded.id
        })
        self.product_id.taxes_id = self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'fiscal_position_id': fiscal_position_inc2ex.id
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        wizard_sol = self.env['rental.wizard'].create({
            'rental_order_line_id': sol.id,
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_sol.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_sol.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_sol.unit_price, 60/1.1, precision_rounding=2), 'Price with 10% taxes should be equal to basic pricing')

        wizard_context = self.env['rental.wizard'].with_context({
            'default_tax_ids': [self.tax_excluded.id]
        }).create({
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_context.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_context.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_context.unit_price, 60/1.1, precision_rounding=2), 'Price with 10% taxes should be equal to basic pricing')

    def test_renting_taxes_ex2inc(self):
        fiscal_position_ex2inc = self.env['account.fiscal.position'].create({'name': 'ex2inc'})
        self.env['account.fiscal.position.tax'].create({
            'position_id': fiscal_position_ex2inc.id,
            'tax_src_id': self.tax_excluded.id,
            'tax_dest_id': self.tax_included.id
        })
        self.product_id.taxes_id = self.tax_excluded

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'fiscal_position_id': fiscal_position_ex2inc.id
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        wizard_sol = self.env['rental.wizard'].create({
            'rental_order_line_id': sol.id,
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_sol.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_sol.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_sol.unit_price, 60*1.1, precision_rounding=2),
                        'Price with included taxes should be equal to basic pricing(tax excluded) + 10% taxes')

        wizard_context = self.env['rental.wizard'].with_context({
            'default_tax_ids': [self.tax_included.id]
        }).create({
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_context.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_context.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_context.unit_price, 60*1.1, precision_rounding=2),
                        'Price with included taxes should be equal to basic pricing(tax excluded) + 10% taxes')

    def test_renting_taxes_included(self):
        self.product_id.taxes_id = self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        wizard_sol = self.env['rental.wizard'].create({
            'rental_order_line_id': sol.id,
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_sol.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_sol.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_sol.unit_price, 60*1.1, precision_rounding=2),
                        'Price in wizard should be equal to basic pricing + 10% (tax included)')

        wizard_context = self.env['rental.wizard'].with_context({
            'default_tax_ids': [self.tax_included.id]
        }).create({
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_context.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_context.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_context.unit_price, 60*1.1, precision_rounding=2),
                        'Price in wizard should be equal to basic pricing + 10% (tax included)')

    def test_renting_taxes_excluded(self):
        self.product_id.taxes_id = self.tax_excluded

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        wizard_sol = self.env['rental.wizard'].create({
            'rental_order_line_id': sol.id,
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_sol.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_sol.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_sol.unit_price, 60, precision_rounding=2),
                        'Price in wizard should be equal to basic pricing (without tax excluded)')

        wizard_context = self.env['rental.wizard'].with_context({
            'default_tax_ids': [self.tax_excluded.id]
        }).create({
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_context.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_context.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_context.unit_price, 60, precision_rounding=2),
                        'Price in wizard should be equal to basic pricing (without tax excluded)')

    def test_renting_taxes_ex_inc(self):
        self.product_id.taxes_id = self.tax_excluded + self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        wizard_sol = self.env['rental.wizard'].create({
            'rental_order_line_id': sol.id,
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_sol.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_sol.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_sol.unit_price, 60*1.1, precision_rounding=2),
                        'Price in wizard should be equal to basic pricing + 10% (tax included)')

        wizard_context = self.env['rental.wizard'].with_context({
            'default_tax_ids': [self.tax_included.id, self.tax_excluded.id]
        }).create({
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_context.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_context.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_context.unit_price, 60*1.1, precision_rounding=2),
                        'Price in wizard should be equal to basic pricing + 10% (tax included)')

    def test_renting_taxes_included_multicompany(self):

        company2 = self.env['res.company'].create({'name': 'Company 2'})
        self.tax_included.company_id = company2

        self.product_id.taxes_id = self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        wizard_sol = self.env['rental.wizard'].create({
            'rental_order_line_id': sol.id,
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_sol.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_sol.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_sol.unit_price, 60, precision_rounding=2),
                        'Included tax related to another company should not apply')

        wizard_context = self.env['rental.wizard'].with_context({
            'default_tax_ids': [self.tax_included.id]
        }).create({
            'product_id': self.product_id.id
        })

        self.assertEqual(wizard_context.duration, 1, 'Default wizard duration should be one day')
        self.assertEqual(wizard_context.duration_unit, 'day', 'Default wizard duration should be one day')

        self.assertTrue(float_compare(wizard_context.unit_price, 60, precision_rounding=2),
                        'Included tax related to another company should not apply')


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_rental_flow(self):
        # somehow, the name_create and onchange of the partner_id
        # in a quotation trigger a re-rendering that loses
        # the focus of some fields, preventing the tour to
        # run successfully if a partner is created during the flow
        # create it in advance here instead
        self.env['res.partner'].name_create('Agrolait')
        self.start_tour("/web", 'rental_tour', login="admin")
