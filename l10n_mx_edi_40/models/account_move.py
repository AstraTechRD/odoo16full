# -*- coding: utf-8 -*-

from odoo import api, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_mx_edi_get_tax_objected(self):
        """Used to determine the IEPS tax breakdown in CFDI
             01 - Used by foreign partners not subject to tax
             02 - Default for MX partners. Splits IEPS taxes
             03 - Special override when IEPS split / Taxes are not required"""
        self.ensure_one()
        customer = self.partner_id if self.partner_id.type == 'invoice' else self.partner_id.commercial_partner_id
        if customer.l10n_mx_edi_no_tax_breakdown:
            return '03'
        elif (self.move_type in self.get_invoice_types() and not self.invoice_line_ids.tax_ids) or \
             (self.move_type == 'entry' and not self._get_reconciled_invoices().invoice_line_ids.tax_ids):
            # the invoice has no taxes OR for payments and bank statement lines, the reconciled invoices have no taxes
            return '01'
        else:
            return '02'

    @api.model
    def _l10n_mx_edi_get_cadena_xslts(self):
        return 'l10n_mx_edi_40/data/4.0/cadenaoriginal_TFD_1_1.xslt', 'l10n_mx_edi_40/data/4.0/cadenaoriginal_4_0.xslt'
