# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    amazon_location = fields.Boolean(
        help="Whether this location represents the stock of a seller managed by Amazon under the "
             "Amazon Fulfillment program or not."
    )
