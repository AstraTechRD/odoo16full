from odoo import models

class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    def js_action_reconcile_st_line(self, st_line_id, params):
        super().js_action_reconcile_st_line(st_line_id, params)
        line = self.env['account.bank.statement.line'].browse(st_line_id)
        if line.partner_id and line.online_partner_information:
            # write value for account and merchant on partner only if partner has no value,
            # in case value are different write False
            value_merchant = line.partner_id.online_partner_information or line.online_partner_information
            value_merchant = value_merchant if value_merchant == line.online_partner_information else False
            line.partner_id.online_partner_information = value_merchant
