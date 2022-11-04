# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def open_action(self):
        # Extends 'account_accountant'
        self.ensure_one()
        if not self._context.get('action_name') and self.type == 'bank' and self.bank_statements_source == 'online_sync':
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                default_context={'search_default_journal_id': self.id},
            )
        return super().open_action()

    def __get_bank_statements_available_sources(self):
        rslt = super(AccountJournal, self).__get_bank_statements_available_sources()
        rslt.append(("online_sync", _("Automated Bank Synchronization")))
        return rslt

    @api.model
    def _get_statement_creation_possible_values(self):
        return [('none', _('Create one statement per synchronization')),
                ('day', _('Create daily statements')),
                ('week', _('Create weekly statements')),
                ('bimonthly', _('Create bi-monthly statements')),
                ('month', _('Create monthly statements'))]

    next_link_synchronization = fields.Datetime("Online Link Next synchronization", related='account_online_link_id.next_refresh')
    expiring_synchronization_date = fields.Date(related='account_online_link_id.expiring_synchronization_date')
    expiring_synchronization_due_day = fields.Integer(compute='_compute_expiring_synchronization_due_day')
    account_online_account_id = fields.Many2one('account.online.account', copy=False, ondelete='set null')
    account_online_link_id = fields.Many2one('account.online.link', related='account_online_account_id.account_online_link_id', readonly=True, store=True)
    account_online_link_state = fields.Selection(related="account_online_link_id.state", readonly=True)

    @api.depends('expiring_synchronization_date')
    def _compute_expiring_synchronization_due_day(self):
        for record in self:
            if record.expiring_synchronization_date:
                due_day_delta = record.expiring_synchronization_date - fields.Date.context_today(record)
                record.expiring_synchronization_due_day = due_day_delta.days
            else:
                record.expiring_synchronization_due_day = 0

    @api.constrains('account_online_account_id')
    def _check_account_online_account_id(self):
        if len(self.account_online_account_id.journal_ids) > 1:
            raise ValidationError(_('You cannot have two journals associated with the same Online Account.'))

    @api.model
    def _cron_fetch_online_transactions(self):
        for journal in self.search([('account_online_account_id', '!=', False)]):
            if journal.account_online_link_id.auto_sync:
                try:
                    journal.with_context(cron=True).manual_sync()
                    # for cron jobs it is usually recommended committing after each iteration,
                    # so that a later error or job timeout doesn't discard previous work
                    self.env.cr.commit()
                except UserError:
                    pass

    def manual_sync(self):
        self.ensure_one()
        if self.account_online_link_id:
            account = self.account_online_account_id
            return self.account_online_link_id.with_context(dont_show_transactions=True)._fetch_transactions(accounts=account)

    def unlink(self):
        """
        Override of the unlink method.
        That's useful to unlink account.online.account too.
        """
        if self.account_online_account_id:
            self.account_online_account_id.unlink()
        return super(AccountJournal, self).unlink()

    def action_configure_bank_journal(self):
        """
        Override the "action_configure_bank_journal" and change the flow for the
        "Configure" button in dashboard.
        """
        return self.env['account.online.link'].action_new_synchronization()

    def action_open_account_online_link(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.account_online_link_id.name,
            'res_model': 'account.online.link',
            'target': 'main',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_id': self.account_online_link_id.id,
        }
