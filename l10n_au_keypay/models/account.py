# -*- coding: utf-8 -*-

from odoo import fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_au_kp_payrun_identifier = fields.Integer('Keypay payrun id', help="Identifier of the keypay payrun that created this move")


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_au_kp_account_identifier = fields.Char('Matching Keypay Account', help="Identifier of the keypay account that matches this account", size=64, index=True)
    l10n_au_kp_enable = fields.Boolean(related="company_id.l10n_au_kp_enable")
