# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_mx_edi_force_generate_cfdi = fields.Boolean(string='Generate CFDI')

    def l10n_mx_edi_update_sat_status(self):
        return self.move_id.l10n_mx_edi_update_sat_status()

    def action_l10n_mx_edi_force_generate_cfdi(self):
        if not self.edi_document_ids:
            self.l10n_mx_edi_force_generate_cfdi = True
            self.move_id._update_payments_edi_documents()
