# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _action_invoice_ready_to_be_sent(self):
        # OVERRIDE
        # Make sure the subscription CRON is called when an invoice becomes ready to be sent by mail.
        res = super()._action_invoice_ready_to_be_sent()

        self.env.ref('sale_subscription.account_analytic_cron_for_invoice')._trigger()

        return res
