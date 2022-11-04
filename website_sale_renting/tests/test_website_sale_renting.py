# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta, FR, SA, SU

from odoo import fields
from odoo.tests import tagged
from .common import TestWebsiteSaleRentingCommon

@tagged('post_install', '-at_install')
class TestWebsiteSaleRenting(TestWebsiteSaleRentingCommon):

    def test_invalid_dates(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
        })
        now = fields.Datetime.now()
        sol = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.computer.id,
            'start_date': now + relativedelta(weekday=SA),
            'return_date': now + relativedelta(weeks=1, weekday=SU),
            'is_rental': True,
        })
        self.assertTrue(sol._is_invalid_renting_dates(sol.company_id), "Pickup and Return dates cannot be the same as renting unavailabilities days")
        sol.write({
            'start_date': now + relativedelta(weekday=FR),
            'return_date': now + relativedelta(weeks=1, weekday=SU),
        })
        self.assertTrue(sol._is_invalid_renting_dates(sol.company_id), "Return date cannot be the same as renting unavailabilities days")
        sol.write({
            'start_date': now + relativedelta(weekday=SU),
            'return_date': now + relativedelta(weeks=1, weekday=SA),
        })
        self.assertTrue(sol._is_invalid_renting_dates(sol.company_id), "Return date cannot be the same as renting unavailabilities days")
        sol.write({
            'start_date': now + relativedelta(weeks=1, weekday=SU),
            'return_date': now,
        })
        self.assertTrue(sol._is_invalid_renting_dates(sol.company_id), "Return date cannot be prior pickupdate")
