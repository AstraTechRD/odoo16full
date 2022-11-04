# -*- coding: utf-8 -*-

import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_mx_edi_clean_to_legal_name(self, name):
        """ We remove the SA de CV / SL de CV / S de RL de CV as they are never in the official name in the XML"""
        res = re.sub(r"(?i:\s+(s\.?[al]\.?|s\.? de r\.?l\.?)"
                     r"( de c\.?v\.?|))\s*$", "", name).upper()
        return res

    def _l10n_mx_edi_get_40_values(self, move):
        customer = move.partner_id if move.partner_id.type == 'invoice' else move.partner_id.commercial_partner_id
        vals = {
            'fiscal_regime': customer.l10n_mx_edi_fiscal_regime,
            'tax_objected': move._l10n_mx_edi_get_tax_objected(),
            'supplier_name': self._l10n_mx_edi_clean_to_legal_name(move.company_id.name),
            'customer_name': self._l10n_mx_edi_clean_to_legal_name(move.commercial_partner_id.name),
        }
        if customer.country_code not in [False, 'MX'] and not vals['fiscal_regime']:
            vals['fiscal_regime'] = '616'
        return vals

    def _l10n_mx_edi_get_invoice_cfdi_values(self, invoice):
        # OVERRIDE
        vals = super()._l10n_mx_edi_get_invoice_cfdi_values(invoice)
        vals.update(self._l10n_mx_edi_get_40_values(invoice))
        return vals

    def _l10n_mx_edi_get_payment_cfdi_values(self, move):
        # OVERRIDE
        vals = super()._l10n_mx_edi_get_payment_cfdi_values(move)
        vals.update(self._l10n_mx_edi_get_40_values(move))
        return vals

    def _l10n_mx_edi_get_invoice_templates(self):
        return 'l10n_mx_edi_40.cfdiv40', 'xsd_cached_cfdv40_xsd'

    def _l10n_mx_edi_get_payment_template(self):
        return 'l10n_mx_edi_40.payment20'

    def _l10n_mx_edi_post_invoice(self, invoices):
        # EXTENDS l10n_mx_edi - rename attachment
        edi_result = super()._l10n_mx_edi_post_invoice(invoices)
        if self.code != 'cfdi_3_3':
            return edi_result
        for invoice in invoices:
            if edi_result[invoice].get('attachment', False):
                cfdi_filename = ('%s-%s-MX-Invoice-4.0.xml' % (invoice.journal_id.code, invoice.payment_reference)).replace('/', '')
                edi_result[invoice]['attachment'].name = cfdi_filename
        return edi_result

    def _l10n_mx_edi_post_payment(self, payments):
        # EXTENDS l10n_mx_edi - rename attachment
        edi_result = super()._l10n_mx_edi_post_payment(payments)
        if self.code != 'cfdi_3_3':
            return edi_result
        for move in payments:
            if edi_result[move].get('attachment', False):
                cfdi_filename = ('%s-%s-MX-Payment-20.xml' % (move.journal_id.code, move.name)).replace('/', '')
                edi_result[move]['attachment'].name = cfdi_filename
        return edi_result
