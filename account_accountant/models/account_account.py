from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def action_open_reconcile(self):
        self.ensure_one()
        # Open reconciliation view for this account
        action_context = {'show_mode_selector': False, 'mode': 'accounts', 'account_ids': [self.id,]}
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }
