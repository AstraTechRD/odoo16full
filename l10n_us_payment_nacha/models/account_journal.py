# coding: utf-8
from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available("nacha"):
            res |= self.env.ref('l10n_us_payment_nacha.account_payment_method_nacha')
        return res

    nacha_immediate_destination = fields.Char(help="This will be provided by your bank.",
                                              string="Immediate Destination")
    nacha_destination = fields.Char(help="This will be provided by your bank.",
                                    string="Destination")
    nacha_immediate_origin = fields.Char(help="This will be provided by your bank.",
                                         string="Immediate Origin")
    nacha_company_identification = fields.Char(help="This will be provided by your bank.",
                                               string="Company Identification")
    nacha_origination_dfi_identification = fields.Char(help="This will be provided by your bank.",
                                                       string="Origination Dfi Identification")
