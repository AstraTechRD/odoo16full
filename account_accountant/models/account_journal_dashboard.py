from odoo import models


class account_journal(models.Model):
    _inherit = "account.journal"

    def action_open_reconcile(self):
        self.ensure_one()

        if self.type in ('bank', 'cash'):
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                default_context={
                    'default_journal_id': self.id,
                    'search_default_journal_id': self.id,
                    'search_default_not_matched': True,
                },
            )
        else:
            # Open reconciliation view for customers/suppliers
            action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
            if self.type == 'sale':
                action_context.update({'mode': 'customers'})
            elif self.type == 'purchase':
                action_context.update({'mode': 'suppliers'})
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }

    def action_open_to_check(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_to_check': True,
                'search_default_journal_id': self.id,
                'default_journal_id': self.id,
            },
        )

    def action_open_bank_transactions(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_journal_id': self.id,
                'default_journal_id': self.id
             },
        )

    def open_action(self):
        if self.type in ('bank', 'cash'):
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                extra_domain=[('journal_id', '=', self.id)],
                default_context={'default_journal_id': self.id},
            )
        return super().open_action()

    def create_cash_statement(self):
        # EXTENDS account
        return self.action_open_bank_transactions()
