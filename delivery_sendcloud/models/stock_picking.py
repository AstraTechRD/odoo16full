# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sendcloud_parcel_ref = fields.Char("Sendcloud Parcel Reference", copy=False)
    sendcloud_return_parcel_ref = fields.Char("Sendcloud Return Parcel Ref", copy=False)
