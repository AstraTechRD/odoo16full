# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    expected_pay_date = fields.Date('Expected Date',
                                    help="Expected payment date as manually set through the customer statement"
                                         "(e.g: if you had the customer on the phone and want to remember the date he promised he would pay)")
