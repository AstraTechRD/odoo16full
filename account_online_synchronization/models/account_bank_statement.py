# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import date_utils


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    online_transaction_identifier = fields.Char("Online Transaction Identifier", readonly=True)
    online_partner_information = fields.Char(readonly=True)
    online_account_id = fields.Many2one(comodel_name='account.online.account', readonly=True)
    online_link_id = fields.Many2one(
        comodel_name='account.online.link',
        related='online_account_id.account_online_link_id',
        store=True,
        readonly=True,
    )

    @api.model
    def _online_sync_bank_statement(self, transactions, online_account):
        """
         build bank statement lines from a list of transaction and post messages is also post in the online_account of the journal.
         :param transactions: A list of transactions that will be created.
             The format is : [{
                 'id': online id,                  (unique ID for the transaction)
                 'date': transaction date,         (The date of the transaction)
                 'name': transaction description,  (The description)
                 'amount': transaction amount,     (The amount of the transaction. Negative for debit, positive for credit)
                 'online_partner_information': optional field used to store information on the statement line under the
                    online_partner_information field (typically information coming from plaid/yodlee). This is use to find partner
                    for next statements
             }, ...]
         :param online_account: The online account for this statement
         Return: The number of imported transaction for the journal
        """
        line_to_reconcile = self.env['account.bank.statement.line']
        amount_sign = -1 if online_account.inverse_transaction_sign else 1
        for journal in online_account.journal_ids:
            # Since the synchronization succeeded, set it as the bank_statements_source of the journal
            journal.sudo().write({'bank_statements_source': 'online_sync'})
            if not transactions:
                continue

            transactions_identifiers = [line['online_transaction_identifier'] for line in transactions]
            existing_transactions_ids = self.env['account.bank.statement.line'].search([('online_transaction_identifier', 'in', transactions_identifiers), ('journal_id', '=', journal.id)])
            existing_transactions = [t.online_transaction_identifier for t in existing_transactions_ids]

            transactions_partner_information = []
            for transaction in transactions:
                transaction['amount'] = transaction['amount'] * amount_sign
                transaction['date'] = fields.Date.from_string(transaction['date'])
                if transaction.get('online_partner_information'):
                    transactions_partner_information.append(transaction['online_partner_information'])

            if transactions_partner_information:
                self._cr.execute("""
                       SELECT p.online_partner_information, p.id FROM res_partner p
                       WHERE p.online_partner_information IN %s AND (p.company_id IS NULL OR p.company_id = %s)
                   """, [tuple(transactions_partner_information), journal.company_id.id])
                partner_id_per_information = dict(self._cr.fetchall())
            else:
                partner_id_per_information = {}

            sorted_transactions = sorted(transactions, key=lambda l: l['date'])
            total = sum([t['amount'] for t in sorted_transactions])

            # For first synchronization, an opening line is created to fill the missing bank statement data
            any_st_line = self.search([('journal_id', '=', journal.id)], limit=1, count=True)
            journal_currency = journal.currency_id or journal.company_id.currency_id
            # If there are neither statement and the ending balance != 0, we create an opening bank statement
            if not any_st_line and not journal_currency.is_zero(online_account.balance - total):
                opening_st_line = self.create({
                    'date': date_utils.subtract(sorted_transactions[0]['date'], days=1),
                    'journal_id': journal.id,
                    'payment_ref': _("Opening statement: first synchronization"),
                    'amount': online_account.balance - total,
                })
                line_to_reconcile += opening_st_line

            st_line_vals_list = []

            for transaction in sorted_transactions:
                if transaction['online_transaction_identifier'] in existing_transactions:
                    continue  # Do nothing if the transaction already exists
                st_line_vals = transaction.copy()
                st_line_vals['online_account_id'] = online_account.id
                st_line_vals['journal_id'] = journal.id

                # Find partner id if exists
                if st_line_vals.get('online_partner_information'):
                    partner_info = st_line_vals['online_partner_information']
                    if partner_id_per_information.get(partner_info):
                        st_line_vals['partner_id'] = partner_id_per_information[partner_info]

                st_line_vals_list.append(st_line_vals)

            if st_line_vals_list:
                line_to_reconcile += self.env['account.bank.statement.line'].create(st_line_vals_list)
            # Set last sync date as the last transaction date
            journal.account_online_account_id.sudo().write({'last_sync': sorted_transactions[-1]['date']})
        return line_to_reconcile
