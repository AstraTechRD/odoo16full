import ast

from odoo import models
from odoo.addons.web.controllers.utils import clean_action


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    def action_open_bank_reconciliation_report(self, journal_id):
        # OVERRIDE account_accountant
        action = self.env['ir.actions.actions']._for_xml_id("account_reports.action_account_report_bank_reconciliation")
        action['context'] = {
            **ast.literal_eval(action['context']),
            'active_model': 'account.journal',
            'active_id': journal_id,
        }
        return clean_action(action, self.env)
