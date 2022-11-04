# -*- coding: utf-8 -*-

from odoo import models


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_invoice_matching_so_candidates(self, st_line, partner):
        """ Find a match between the bank transaction and some sale orders. If none of them are invoiced, there are
        returned to display a message to the user allowing him to show the matched sale orders.
        If some of them are already matched, the journal items are suggested to the user.

        :param st_line: A statement line.
        :param partner: The partner to consider.
        :return:
            {'allow_auto_reconcile': <bool>, 'amls': <account.move.line>} if some sale orders are invoiced.
            {'sale_orders': <sale.order>} otherwise.
        """
        assert self.rule_type == 'invoice_matching'
        for model in ('sale.order', 'sale.order.line', 'account.move', 'account.move.line'):
            self.env[model].flush_model()

        st_line_text_values = st_line._get_st_line_strings_for_matching(allowed_fields=(
            'payment_ref' if self.match_text_location_label else None,
            'narration' if self.match_text_location_note else None,
            'ref' if self.match_text_location_reference else None,
        ))
        if not st_line_text_values:
            return

        additional_conditions = []
        params = []
        for text_value in st_line_text_values:
            additional_conditions.append(r'''
                (
                    sale_order.name IS NOT NULL
                    AND SUBSTRING(REGEXP_REPLACE(LOWER(%s), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*')
                        ~ SUBSTRING(REGEXP_REPLACE(LOWER(sale_order.name), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*')
                ) OR (
                    sale_order.reference IS NOT NULL
                    AND SUBSTRING(REGEXP_REPLACE(LOWER(%s), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*')
                        ~ SUBSTRING(REGEXP_REPLACE(LOWER(sale_order.reference), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*')
                )
            ''')
            params += [text_value, text_value]

        if self.matching_order == 'new_first':
            aml_order_by = 'account_move_line.date_maturity DESC, account_move_line.date DESC, account_move_line.id DESC'
            so_order_by = 'sale_order.date_order DESC, sale_order.id DESC'
        else:
            aml_order_by = 'account_move_line.date_maturity ASC, account_move_line.date ASC, account_move_line.id ASC'
            so_order_by = 'sale_order.date_order ASC, sale_order.id ASC'

        aml_domain = self._get_invoice_matching_amls_domain(st_line, partner)
        query = self.env['account.move.line']._where_calc(aml_domain)
        _aml_tables, aml_where_clause, aml_where_params = query.get_sql()

        # Find the existing amls from sale orders.
        query = self.env['sale.order']._where_calc([
            ('company_id', '=', st_line.company_id.id),
            '|',
            ('invoice_status', '=', 'invoiced'),
            ('state', '=', 'sent'),
        ])
        so_tables, so_where_clause, so_where_params = query.get_sql()

        self._cr.execute(
            f'''
                SELECT account_move_line.id
                FROM {so_tables}
                JOIN sale_order_line so_line ON so_line.order_id = sale_order.id
                JOIN sale_order_line_invoice_rel rel ON rel.order_line_id = so_line.id
                JOIN account_move_line inv_line ON inv_line.id = rel.invoice_line_id
                JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = inv_line.move_id
                JOIN account_move_line ON account_move_line.move_id = account_move_line__move_id.id
                WHERE {so_where_clause}
                    AND {aml_where_clause}
                    AND (''' + ' OR '.join(additional_conditions) + f''')
                ORDER BY {aml_order_by}
            ''',
            so_where_params + aml_where_params + params,
        )
        seen_ids = set()
        candidate_ids = []
        for row in self._cr.fetchall():
            aml_id = row[0]
            if aml_id not in seen_ids:
                candidate_ids.append(aml_id)
                seen_ids.add(aml_id)
        if candidate_ids:
            return {
                'allow_auto_reconcile': True,
                'amls': self.env['account.move.line'].browse(candidate_ids),
            }

        # Find the sale orders that are not yet invoiced.
        query = self.env['sale.order']._where_calc([
            ('company_id', '=', st_line.company_id.id),
            '|',
            ('invoice_status', '=', 'to invoice'),
            ('state', '=', 'sent'),
        ])
        so_tables, so_where_clause, so_where_params = query.get_sql()

        self._cr.execute(
            f'''
                SELECT sale_order.id
                FROM {so_tables}
                WHERE {so_where_clause} AND (''' + ' OR '.join(additional_conditions) + f''')
                ORDER BY {so_order_by}
            ''',
            so_where_params + params,
        )
        candidate_ids = [r[0] for r in self._cr.fetchall()]
        if candidate_ids:
            return {
                'sale_orders': self.env['sale.order'].browse(candidate_ids),
            }

    def _get_invoice_matching_rules_map(self):
        # EXTENDS account
        res = super()._get_invoice_matching_rules_map()
        res[0].append(self._get_invoice_matching_so_candidates)
        return res
