# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AvataxPaymentLinkWizard(models.TransientModel):
    _inherit = "payment.link.wizard"

    @api.model
    def default_get(self, fields):
        res_id = self._context['active_id']
        res_model = self._context['active_model']

        # Both sale.order and account.move implement button_update_avatax.
        # This also ensures that tax validation works (e.g. customer has valid address, ...).
        # Otherwise errors will occur during record validation.
        self.env[res_model].browse(res_id).button_update_avatax()

        return super(AvataxPaymentLinkWizard, self).default_get(fields)
