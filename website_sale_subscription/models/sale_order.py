# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_order_line_values(self, product_id, quantity, **kwargs):
        """ Update the SO's recurrence
        """
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)
        product = self.env['product.product'].browse(product_id)
        if product.recurring_invoice:
            pricelist = self.env['website'].get_current_website().get_current_pricelist()
            pricing = self.env['product.pricing']._get_first_suitable_pricing(product, pricelist)
            self.recurrence_id = pricing.recurrence_id
        return values
