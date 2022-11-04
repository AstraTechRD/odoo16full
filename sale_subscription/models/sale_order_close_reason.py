# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderCloseReason(models.Model):
    _name = "sale.order.close.reason"
    _order = "sequence, id"
    _description = "Subscription Close Reason"

    name = fields.Char('Reason', required=True, translate=True)
    sequence = fields.Integer(default=10)
