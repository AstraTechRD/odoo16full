# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _lt, models

class ProductPricing(models.Model):
    _inherit = 'product.pricing'

    def _get_unit_label(self, duration):
        """ Get the product pricing unit label for website rendering. """
        if duration is None:
            return ""
        labels = {
            'hour': _lt("Hour"),
            'day': _lt("Day"),
            'week': _lt("Week"),
            'month': _lt("Month"),
        }
        if self.recurrence_id.unit in labels:
            return labels[self.recurrence_id.unit]
        return dict(self.env['sale.temporal.recurrence']._fields['unit']._description_selection(self.env))[self.recurrence_id.unit]
