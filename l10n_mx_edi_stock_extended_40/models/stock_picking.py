# -*- coding: utf-8 -*-

from odoo import models

from .product_template import MX_PACKAGING_CATALOG

class Picking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_mx_edi_get_packaging_desc(self, code):
        return dict(MX_PACKAGING_CATALOG).get(code, None)
