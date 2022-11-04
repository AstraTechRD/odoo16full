# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', related='company_id.nomenclature_id', readonly=False)
