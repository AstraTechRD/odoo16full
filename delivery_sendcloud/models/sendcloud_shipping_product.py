# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class SendCloudShippingProduct(models.Model):

    _name = "sendcloud.shipping.product"
    _description = "Choose from the available sendcloud shipping methods"

    name = fields.Char(string="Shipping Product", required=True)
    sendcloud_id = fields.Integer(string="External Sendcloud Id", required=True)
    carrier = fields.Char(string="Shipping Carrier")
    min_weight = fields.Float(string="Minimum Weight")
    max_weight = fields.Float(string="Maximum Weight")
