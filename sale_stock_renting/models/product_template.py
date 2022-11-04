# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Padding Time

    preparation_time = fields.Float(string="Security Time", company_dependent=True,
                                    help="Temporarily make this product unavailable before pickup.")

    @api.constrains('rent_ok', 'tracking')
    def _lot_not_supported_rental(self):
        for template in self:
            if template.rent_ok and template.tracking == 'lot':
                raise ValidationError(_(
                    "Tracking by lots isn't supported for rental products."
                    "\nYou should rather change the tracking mode to unique serial numbers."
                ))

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for template in self:
            if template.rent_ok and not template.sale_ok:
                template.show_forecasted_qty_status_button = False
