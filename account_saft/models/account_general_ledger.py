# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo.tools import float_repr, get_lang
from odoo import api, fields, models, release, _
from odoo.exceptions import UserError


class AccountGeneralLedger(models.AbstractModel):
    _inherit = "account.report"

    @api.model
    def _saft_fill_report_general_ledger_values(self, options, values):
        res = {
            'total_debit_in_period': 0.0,
            'total_credit_in_period': 0.0,
            'account_vals_list': [],
            'journal_vals_list': [],
            'move_vals_list': [],
            'tax_detail_per_line_map': {},
        }

        # Fill 'account_vals_list'.
        handler = self.env['account.general.ledger.report.handler']
        accounts_results = handler._query_values(self, options)
        rslts_array = tuple((account, res_col_gr[options['single_column_group']]) for account, res_col_gr in accounts_results)
        init_bal_res = handler._get_initial_balance_values(self, tuple(account.id for account, results in rslts_array), options)
        initial_balances_map = {}
        initial_balance_gen = ((account, init_bal_dict.get(options['single_column_group'])) for account, init_bal_dict in init_bal_res.values())
        for account, initial_balance in initial_balance_gen:
            initial_balances_map[account.id] = initial_balance
        for account, results in rslts_array:
            account_init_bal = initial_balances_map[account.id]
            account_un_earn = results.get('unaffected_earnings', {})
            account_balance = results.get('sum', {})
            opening_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
            closing_balance = account_balance.get('balance', 0.0)
            res['account_vals_list'].append({
                'account': account,
                'account_type': dict(self.env['account.account']._fields['account_type']._description_selection(self.env))[account.account_type],
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })
        # Fill 'total_debit_in_period', 'total_credit_in_period', 'move_vals_list'.
        tables, where_clause, where_params = self._query_get(options, 'strict_range')
        lang = self.env.user.lang or get_lang(self.env).code
        tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
            self.pool['account.tax'].name.translate else 'tax.name'
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        uom_name = f"""COALESCE(uom.name->>'{lang}', uom.name->>'en_US')"""
        query = f'''
            SELECT
                account_move_line.id,
                account_move_line.display_type,
                account_move_line.date,
                account_move_line.name,
                account_move_line.account_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.debit,
                account_move_line.credit,
                account_move_line.balance,
                account_move_line.tax_line_id,
                account_move_line.quantity,
                account_move_line.price_unit,
                account_move_line.product_id,
                account_move_line.product_uom_id,
                account_move.id                             AS move_id,
                account_move.name                           AS move_name,
                account_move.move_type                      AS move_type,
                account_move.create_date                    AS move_create_date,
                account_move.invoice_date                   AS move_invoice_date,
                account_move.invoice_origin                 AS move_invoice_origin,
                tax.id                                      AS tax_id,
                {tax_name}                                  AS tax_name,
                tax.amount                                  AS tax_amount,
                tax.amount_type                             AS tax_amount_type,
                journal.id                                  AS journal_id,
                journal.code                                AS journal_code,
                {journal_name}                              AS journal_name,
                journal.type                                AS journal_type,
                account.account_type                        AS account_type,
                currency.name                               AS currency_code,
                product.default_code                        AS product_default_code,
                {uom_name}                                  AS product_uom_name
            FROM ''' + tables + '''
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            JOIN res_currency currency ON currency.id = account_move_line.currency_id
            LEFT JOIN product_product product ON product.id = account_move_line.product_id
            LEFT JOIN uom_uom uom ON uom.id = account_move_line.product_uom_id
            LEFT JOIN account_tax tax ON tax.id = account_move_line.tax_line_id
            WHERE ''' + where_clause + '''
            ORDER BY account_move_line.date, account_move_line.id
        '''
        self._cr.execute(query, where_params)

        journal_vals_map = {}
        move_vals_map = {}
        inbound_types = self.env['account.move'].get_inbound_types(include_receipts=True)
        for line_vals in self._cr.dictfetchall():
            line_vals['rate'] = abs(line_vals['amount_currency']) / abs(line_vals['balance']) if line_vals['balance'] else 1.0
            line_vals['tax_detail_vals_list'] = []

            journal_vals_map.setdefault(line_vals['journal_id'], {
                'id': line_vals['journal_id'],
                'name': line_vals['journal_name'],
                'type': line_vals['journal_type'],
                'move_vals_map': {},
            })
            journal_vals = journal_vals_map[line_vals['journal_id']]

            move_vals = {
                'id': line_vals['move_id'],
                'name': line_vals['move_name'],
                'type': line_vals['move_type'],
                'sign': -1 if line_vals['move_type'] in inbound_types else 1,
                'invoice_date': line_vals['move_invoice_date'],
                'invoice_origin': line_vals['move_invoice_origin'],
                'date': line_vals['date'],
                'create_date': line_vals['move_create_date'],
                'partner_id': line_vals['partner_id'],
                'line_vals_list': [],
            }
            move_vals_map.setdefault(line_vals['move_id'], move_vals)
            journal_vals['move_vals_map'].setdefault(line_vals['move_id'], move_vals)

            move_vals = move_vals_map[line_vals['move_id']]
            move_vals['line_vals_list'].append(line_vals)

            # Track the total debit/period of the whole period.
            res['total_debit_in_period'] += line_vals['debit']
            res['total_credit_in_period'] += line_vals['credit']

            res['tax_detail_per_line_map'][line_vals['id']] = line_vals

        # Fill 'journal_vals_list'.
        for journal_vals in journal_vals_map.values():
            journal_vals['move_vals_list'] = list(journal_vals.pop('move_vals_map').values())
            res['journal_vals_list'].append(journal_vals)
            res['move_vals_list'] += journal_vals['move_vals_list']

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _saft_fill_report_tax_details_values(self, options, values):
        tax_vals_map = {}

        tables, where_clause, where_params = self._query_get(options, 'strict_range')
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)
        if self.pool['account.tax'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')"
        else:
            tax_name = 'tax.name'
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)
        self._cr.execute(f'''
            SELECT
                tax_detail.base_line_id,
                tax_line.currency_id,
                tax.id AS tax_id,
                tax.amount_type AS tax_amount_type,
                {tax_name} AS tax_name,
                tax.amount AS tax_amount,
                SUM(tax_detail.tax_amount) AS amount,
                SUM(tax_detail.tax_amount) AS amount_currency
            FROM ({tax_details_query}) AS tax_detail
            JOIN account_move_line tax_line ON tax_line.id = tax_detail.tax_line_id
            JOIN account_tax tax ON tax.id = tax_detail.tax_id
            GROUP BY tax_detail.base_line_id, tax_line.currency_id, tax.id
        ''', tax_details_params)
        for tax_vals in self._cr.dictfetchall():
            line_vals = values['tax_detail_per_line_map'][tax_vals['base_line_id']]
            line_vals['tax_detail_vals_list'].append({
                **tax_vals,
                'rate': line_vals['rate'],
                'currency_code': line_vals['currency_code'],
            })
            tax_vals_map.setdefault(tax_vals['tax_id'], {
                'id': tax_vals['tax_id'],
                'name': tax_vals['tax_name'],
                'amount': tax_vals['tax_amount'],
                'amount_type': tax_vals['tax_amount_type'],
            })

        # Fill 'tax_vals_list'.
        values['tax_vals_list'] = list(tax_vals_map.values())

    @api.model
    def _saft_fill_report_partner_ledger_values(self, options, values):
        res = {
            'customer_vals_list': [],
            'supplier_vals_list': [],
            'partner_detail_map': defaultdict(lambda: {
                'type': False,
                'addresses': [],
                'contacts': [],
            }),
        }

        all_partners = self.env['res.partner']

        # Fill 'customer_vals_list' and 'supplier_vals_list'
        report = self.env.ref('account_reports.partner_ledger_report')
        new_options = report._get_options(options)
        new_options['account_type'] = [
            {'id': 'trade_receivable', 'selected': True},
            {'id': 'non_trade_receivable', 'selected': True},
            {'id': 'trade_payable', 'selected': True},
            {'id': 'non_trade_payable', 'selected': True},
        ]
        handler = self.env['account.partner.ledger.report.handler']
        partners_results = handler._query_partners(new_options)
        partner_vals_list = []
        rslts_array = tuple((partner, res_col_gr[options['single_column_group']]) for partner, res_col_gr in partners_results)
        init_bal_res = handler._get_initial_balance_values(tuple(partner.id for partner, results in rslts_array), options)
        initial_balances_map = {}
        initial_balance_gen = ((partner_id, init_bal_dict.get(options['single_column_group'])) for partner_id, init_bal_dict in init_bal_res.items())

        for partner_id, initial_balance in initial_balance_gen:
            initial_balances_map[partner_id] = initial_balance
        for partner, results in rslts_array:
            # Ignore Falsy partner.
            if not partner:
                continue

            all_partners |= partner
            partner_init_bal = initial_balances_map[partner.id]

            opening_balance = partner_init_bal.get('balance', 0.0)
            closing_balance = results.get('balance', 0.0)
            partner_vals_list.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        if all_partners:
            domain = [('partner_id', 'in', tuple(all_partners.ids))]
            tables, where_clause, where_params = self._query_get(new_options, 'strict_range', domain=domain)
            self._cr.execute(f'''
                SELECT
                    account_move_line.partner_id,
                    SUM(account_move_line.balance)
                FROM {tables}
                JOIN account_account account ON account.id = account_move_line.account_id
                WHERE {where_clause}
                AND account.account_type IN ('asset_receivable', 'liability_payable')
                GROUP BY account_move_line.partner_id
            ''', where_params)

            for partner_id, balance in self._cr.fetchall():
                res['partner_detail_map'][partner_id]['type'] = 'customer' if balance >= 0.0 else 'supplier'

        for partner_vals in partner_vals_list:
            partner_id = partner_vals['partner'].id
            if res['partner_detail_map'][partner_id]['type'] == 'customer':
                res['customer_vals_list'].append(partner_vals)
            elif res['partner_detail_map'][partner_id]['type'] == 'supplier':
                res['supplier_vals_list'].append(partner_vals)

        # Fill 'partner_detail_map'.
        all_partners |= values['company'].partner_id
        partner_addresses_map = defaultdict(dict)
        partner_contacts_map = defaultdict(lambda: self.env['res.partner'])

        def _track_address(current_partner, partner):
            if partner.zip and partner.city:
                address_key = (partner.zip, partner.city)
                partner_addresses_map[current_partner][address_key] = partner

        def _track_contact(current_partner, partner):
            phone = partner.phone or partner.mobile
            if phone:
                partner_contacts_map[current_partner] |= partner

        for partner in all_partners:
            _track_address(partner, partner)
            _track_contact(partner, partner)
            for child in partner.child_ids:
                _track_address(partner, child)
                _track_contact(partner, child)

        no_partner_address = self.env['res.partner']
        no_partner_contact = self.env['res.partner']
        for partner in all_partners:
            res['partner_detail_map'][partner.id].update({
                'partner': partner,
                'addresses': list(partner_addresses_map[partner].values()),
                'contacts': partner_contacts_map[partner],
            })
            if not res['partner_detail_map'][partner.id]['addresses']:
                no_partner_address |= partner
            if not res['partner_detail_map'][partner.id]['contacts']:
                no_partner_contact |= partner

        if no_partner_address:
            raise UserError(_(
                    "Please define at least one address (Zip/City) for the following partners: %s.",
                    ', '.join(no_partner_address.mapped('display_name')),
            ))
        if no_partner_contact:
            raise UserError(_(
                    "Please define at least one contact (Phone or Mobile) for the following partners: %s.",
                    ', '.join(no_partner_contact.mapped('display_name')),
            ))

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _saft_prepare_report_values(self, options):
        def format_float(amount, digits=2):
            return float_repr(amount or 0.0, precision_digits=digits)

        def format_date(date_str, formatter):
            date_obj = fields.Date.to_date(date_str)
            return date_obj.strftime(formatter)

        company = self.env.company
        if not company.company_registry:
            raise UserError(_("Please define `Company Registry` for your company."))

        if len(options["column_groups"]) > 1:
            raise UserError(_("SAFT is only compatible with one column group."))

        options["single_column_group"] = tuple(options["column_groups"].keys())[0]

        template_values = {
            'company': company,
            'xmlns': '',
            'file_version': 'undefined',
            'accounting_basis': 'undefined',
            'today_str': fields.Date.to_string(fields.Date.context_today(self)),
            'software_version': release.version,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'format_float': format_float,
            'format_date': format_date,
        }
        self._saft_fill_report_general_ledger_values(options, template_values)
        self._saft_fill_report_tax_details_values(options, template_values)
        self._saft_fill_report_partner_ledger_values(options, template_values)
        return template_values
