# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _enable_temporal_price(self, start_date=None, end_date=None, duration=None, unit=None):
        """ Override to force the computation through rental price from website """
        return super()._enable_temporal_price(start_date, end_date, duration, unit)\
            or self.env.context.get('website_id')
