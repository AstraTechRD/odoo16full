# coding: utf-8
from odoo import api, models, _
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.constrains("ref", "payment_method_line_id")
    def _check_ref(self):
        for payment in self:
            if not payment.ref and payment.payment_method_code == "nacha":
                raise ValidationError(_("NACHA payments require a memo"))

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_using_bank_account()
        res.append('nacha')
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_needing_bank_account()
        res.append('nacha')
        return res
