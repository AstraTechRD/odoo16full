# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import str2bool

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # used to control the renewal flow based on the transaction state
    renewal_allowed = fields.Boolean(
        compute='_compute_renewal_allowed', store=False)

    @api.depends('state')
    def _compute_renewal_allowed(self):
        for tx in self:
            tx.renewal_allowed = tx.state in ('done', 'authorized')

    def _reconcile_after_done(self):
        res = super()._reconcile_after_done()
        if str2bool(self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice')):
            today = fields.Date.today()
            order_to_update_ids = self.env['sale.order']
            for order in self.sale_order_ids:
                if order.recurrence_id and order.payment_token_id and order.start_date <= order.next_invoice_date <= today:
                    order_to_update_ids |= order
            order_to_update_ids._update_next_invoice_date()
        return res


class PaymentToken(models.Model):
    _name = 'payment.token'
    _inherit = 'payment.token'

    def _handle_archiving(self):
        """ Override of payment to void the token on linked subscriptions.

        :return: None
        """
        super()._handle_archiving()

        linked_subscriptions = self.env['sale.order'].search([('payment_token_id', 'in', self.ids)])
        linked_subscriptions.write({'payment_token_id': None})

    def get_linked_records_info(self):
        """ Override of payment to add information about subscriptions linked to the current token.

        Note: self.ensure_one()

        :return: The list of information about linked subscriptions
        :rtype: list
        """
        res = super().get_linked_records_info()
        subscriptions = self.env['sale.order'].search([('payment_token_id', '=', self.id)])
        for sub in subscriptions:
            res.append({
                'description': subscriptions._description,
                'id': sub.id,
                'name': sub.name,
                'url': sub.get_portal_url()
            })
        return res
