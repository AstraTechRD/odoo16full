# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fedex_access_point_address = fields.Text('Fedex Address')

    def get_fedex_access_point_address(self):
        if self.fedex_access_point_address:
            return json.loads(self.fedex_access_point_address)
        return False

    def write(self, values):
        access_point = values.get('fedex_access_point_address')
        if access_point:
            values['fedex_access_point_address'] = access_point
        return super(SaleOrder, self).write(values)
