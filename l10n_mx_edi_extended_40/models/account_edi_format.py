# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_mx_edi_get_invoice_cfdi_values(self, invoice):
        # OVERRIDE
        vals = super()._l10n_mx_edi_get_invoice_cfdi_values(invoice)
        vals['l10n_mx_edi_external_trade_type'] = invoice.l10n_mx_edi_external_trade_type or '01'
        return vals
