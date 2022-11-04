# -*- coding: utf-8 -*-

import re
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountLinkJournalLine(models.TransientModel):
    _name = "account.link.journal.line"
    _description = "Link one bank account to a journal"

    journal_id = fields.Many2one('account.journal', domain="[('type', '=', 'bank'), ('account_online_account_id', '=', False)]")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    online_account_id = fields.Many2one('account.online.account')
    name = fields.Char(related='online_account_id.name', string="Account name", readonly=False)
    balance = fields.Float(related='online_account_id.balance', readonly=True)
    account_online_wizard_id = fields.Many2one('account.link.journal')
    account_number = fields.Char(related='online_account_id.account_number', readonly=False)

    def unlink(self):
        self.mapped('online_account_id').filtered(lambda acc: not acc.journal_ids).unlink()
        return super(AccountLinkJournalLine, self).unlink()

    @api.onchange('journal_id')
    def _onchange_action(self):
        if self.journal_id:
            if self.journal_id.type != 'bank':
                raise UserError(_('Journals linked to a bank account must be of the bank type.'))
            self.currency_id = self.journal_id.currency_id.id

    @api.model_create_multi
    def create(self, vals_list):
        def get_journal_id(journal_account_numbers, online_account):
            online_account_number = sanitize_account_number(online_account.account_number) if online_account.account_number else ''
            if online_account_number:
                regex = re.compile('.*' + online_account_number)
                for number, journal in journal_account_numbers.items():
                    if regex.match(number) and (not journal.currency_id or not online_account.currency_id or journal.currency_id.id == online_account.currency_id.id):
                        return journal_account_numbers.pop(number).id
            if online_account.currency_id and online_account.currency_id.id in empty_journals_by_currency.keys() and empty_journals_by_currency.get(online_account.currency_id.id):
                return empty_journals_by_currency[online_account.currency_id.id].pop(0)
            elif empty_journals_by_currency['no_currency']:
                return empty_journals_by_currency['no_currency'].pop(0)
            return None

        bank_journals = self.env['account.journal'].search([('type', '=', 'bank'), ('account_online_account_id', '=', False)])
        journals_with_local_account = bank_journals.filtered(lambda journal: journal.bank_account_id)
        journal_with_amls = self.env['account.journal'].browse([j.get('journal_id')[0] for j in self.env['account.move.line'].read_group(fields=['journal_id'], groupby=['journal_id'], domain=[])])
        empty_journals_without_bank_account = bank_journals - journals_with_local_account - journal_with_amls

        journal_account_numbers = {journal.bank_account_id.sanitized_acc_number: journal for journal in journals_with_local_account}
        empty_journals_by_currency = {'no_currency': []}

        for journal in empty_journals_without_bank_account:
            code = journal.currency_id.id
            if not code:
                empty_journals_by_currency['no_currency'].append(journal.id)
            elif empty_journals_by_currency.get(code):
                empty_journals_by_currency[code].append(journal.id)
            else:
                empty_journals_by_currency[code] = [journal.id]

        for vals in vals_list:
            online_account = self.env['account.online.account'].browse(vals['online_account_id'])
            if online_account.currency_id:
                vals['currency_id'] = online_account.currency_id.id

            vals['journal_id'] = get_journal_id(journal_account_numbers, online_account)
        return super().create(vals_list)

class AccountLinkJournal(models.TransientModel):
    _name = "account.link.journal"
    _description = "Link list of bank accounts to journals"

    number_added = fields.Integer(readonly=True)
    transactions = fields.Html(readonly=True)
    sync_date = fields.Date('Get transactions since', default=lambda a: fields.Date.context_today(a) - relativedelta(days=15))
    account_ids = fields.One2many('account.link.journal.line', 'account_online_wizard_id', 'Synchronized accounts')

    def unlink(self):
        self.mapped('account_ids').unlink()
        return super(AccountLinkJournal, self).unlink()

    def _get_journal_values(self, account, create=False):
        vals = {
            'account_online_account_id': account.online_account_id.id,
            'bank_statements_source': 'online_sync',
            'currency_id': account.currency_id.id,
        }
        if account.account_number:
            vals['bank_acc_number'] = account.account_number

        # Remove currency from the dict if it has not changed as it might trigger an error if there are entries
        # with another currency in this journal.
        if account.journal_id.currency_id.id == vals['currency_id']:
            vals.pop('currency_id', None)
        return vals

    def sync_now(self):
        """
        This method is called when the user click on "Synchronize now".
        """
        # Link account to journal
        journal_already_linked = []
        if not len(self.account_ids):
            return {'type': 'ir.actions.act_window_close'}
        for account in self.account_ids:
            account.online_account_id.write({'last_sync': self.sync_date})
            if not account.journal_id:
                new_journal_code = self.env['account.journal'].get_next_bank_cash_default_code('bank', self.env.company)
                account.journal_id = self.env['account.journal'].create({
                    'name': account.account_number or account.display_name,
                    'code': new_journal_code,
                    'type': 'bank',
                    'company_id': self.env.company.id,
                })
            if account.journal_id.id in journal_already_linked:
                raise UserError(_('You can not link two accounts to the same journal.'))
            journal_already_linked.append(account.journal_id.id)
            account.journal_id.write(self._get_journal_values(account))
        # Call to synchronize
        online_account_ids = self.account_ids.mapped('online_account_id')
        return online_account_ids.mapped('account_online_link_id').action_fetch_transactions()

    def cancel_sync(self):
        # Remove account_online_account if the user cancel the link
        self.account_ids.unlink()
        return {'type': 'ir.actions.act_window_close'}
