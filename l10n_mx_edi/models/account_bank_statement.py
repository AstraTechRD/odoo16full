# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    l10n_mx_edi_force_generate_cfdi = fields.Boolean(string='Generate CFDI')

    def action_l10n_mx_edi_force_generate_cfdi(self):
        self.l10n_mx_edi_force_generate_cfdi = True
        self.move_id._update_payments_edi_documents()
