# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo import api, models, Command
from odoo.addons.base_import.models.base_import import FIELDS_RECURSION_LIMIT


class AccountBankStmtImportCSV(models.TransientModel):

    _inherit = 'base_import.import'

    @api.model
    def get_fields_tree(self, model, depth=FIELDS_RECURSION_LIMIT):
        fields_list = super(AccountBankStmtImportCSV, self).get_fields_tree(model, depth=depth)
        if self._context.get('bank_stmt_import', False):
            add_fields = [{
                'id': 'balance',
                'name': 'balance',
                'string': 'Cumulative Balance',
                'required': False,
                'fields': [],
                'type': 'monetary',
            }, {
                'id': 'debit',
                'name': 'debit',
                'string': 'Debit',
                'required': False,
                'fields': [],
                'type': 'monetary',
            }, {
                'id': 'credit',
                'name': 'credit',
                'string': 'Credit',
                'required': False,
                'fields': [],
                'type': 'monetary',
            }]
            fields_list.extend(add_fields)
        return fields_list

    def _convert_to_float(self, value):
        return float(value) if value else 0.0

    def _parse_import_data(self, data, import_fields, options):
        # EXTENDS base
        data = super()._parse_import_data(data, import_fields, options)
        journal_id = self._context.get('default_journal_id')
        if not journal_id:
            return data

        journal = self.env['account.journal'].browse(journal_id)
        statement_vals = options['statement_vals'] = {}

        ret_data = []

        import_fields.append('sequence')
        index_balance = False
        convert_to_amount = False
        if 'debit' in import_fields and 'credit' in import_fields:
            index_debit = import_fields.index('debit')
            index_credit = import_fields.index('credit')
            self._parse_float_from_data(data, index_debit, 'debit', options)
            self._parse_float_from_data(data, index_credit, 'credit', options)
            import_fields.append('amount')
            import_fields.remove('debit')
            import_fields.remove('credit')
            convert_to_amount = True

        # add starting balance and ending balance to context
        if 'balance' in import_fields:
            index_balance = import_fields.index('balance')
            self._parse_float_from_data(data, index_balance, 'balance', options)
            statement_vals['balance_start'] = self._convert_to_float(data[0][index_balance])
            statement_vals['balance_start'] -= self._convert_to_float(data[0][import_fields.index('amount')]) \
                                            if not convert_to_amount \
                                            else abs(self._convert_to_float(data[0][index_credit]))-abs(self._convert_to_float(data[0][index_debit]))
            statement_vals['balance_end_real'] = data[len(data)-1][index_balance]
            import_fields.remove('balance')

        currency_index = 'foreign_currency_id' in import_fields and import_fields.index('foreign_currency_id') or False
        for index, line in enumerate(data):
            line.append(index)
            remove_index = []
            if convert_to_amount:
                line.append(
                    abs(self._convert_to_float(line[index_credit]))
                    - abs(self._convert_to_float(line[index_debit]))
                )
                remove_index.extend([index_debit, index_credit])
            if index_balance:
                remove_index.append(index_balance)
            # Remove added field debit/credit/balance
            for index in sorted(remove_index, reverse=True):
                line.remove(line[index])
            if line[import_fields.index('amount')]:
                ret_data.append(line)
            # Don't set the currency_id on statement line if the currency is the same as the company one.
            if currency_index is not False and line[currency_index] == (journal.currency_id or journal.company_id.currency_id).name:
                line[currency_index] = False

        return ret_data

    def parse_preview(self, options, count=10):
        if options.get('bank_stmt_import', False):
            self = self.with_context(bank_stmt_import=True)
        return super(AccountBankStmtImportCSV, self).parse_preview(options, count=count)

    def execute_import(self, fields, columns, options, dryrun=False):
        if options.get('bank_stmt_import'):
            self._cr.execute('SAVEPOINT import_bank_stmt')
            res = super().execute_import(fields, columns, options, dryrun=dryrun)
            statement = self.env['account.bank.statement'].create({
                'reference': self.file_name,
                'line_ids': [Command.set(res.get('ids', []))],
                **options.get('statement_vals', {}),
            })

            try:
                if dryrun:
                    self._cr.execute('ROLLBACK TO SAVEPOINT import_bank_stmt')
                else:
                    self._cr.execute('RELEASE SAVEPOINT import_bank_stmt')
                    res['messages'].append({
                        'statement_id': statement.id,
                        'type': 'bank_statement'
                        })
            except psycopg2.InternalError:
                pass
            return res
        else:
            return super(AccountBankStmtImportCSV, self).execute_import(fields, columns, options, dryrun=dryrun)
