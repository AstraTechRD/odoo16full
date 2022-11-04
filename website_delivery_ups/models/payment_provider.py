# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Paymentprovider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(
        selection_add=[('cash_on_delivery', 'Cash On Delivery')]
    )

    @api.model
    def _get_compatible_providers(self, *args, sale_order_id=None, **kwargs):
        """ Override of payment to exclude COD providers if the delivery doesn't match.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        compatible_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, **kwargs
        )
        sale_order = self.env['sale.order'].browse(sale_order_id).exists()
        if sale_order.carrier_id.delivery_type != 'ups' or not sale_order.carrier_id.ups_cod:
            compatible_providers.filtered(
                lambda p: p.code != 'custom' or p.custom_mode != 'cash_on_delivery'
            )

        return compatible_providers
