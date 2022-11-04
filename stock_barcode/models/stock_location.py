# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class Location(models.Model):
    _inherit = 'stock.location'
    _barcode_field = 'barcode'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = self.env.company.nomenclature_id._preprocess_gs1_search_args(args, ['location', 'location_dest'])
        return super()._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.model
    def _get_fields_stock_barcode(self):
        return ['barcode', 'display_name', 'name', 'parent_path', 'usage']
