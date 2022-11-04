# -*- coding: utf-8 -*-

from odoo import models


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_invoice_matching_batch_payments_candidates(self, st_line, partner):
        assert self.rule_type == 'invoice_matching'
        self.env['account.batch.payment'].flush_model()

        st_line_text_values = st_line._get_st_line_strings_for_matching(allowed_fields=(
            'payment_ref' if self.match_text_location_label else None,
            'narration' if self.match_text_location_note else None,
            'ref' if self.match_text_location_reference else None,
        ))
        if not st_line_text_values:
            return

        if self.matching_order == 'new_first':
            order_by = 'account_move_line.date_maturity DESC, account_move_line.date DESC, account_move_line.id DESC'
        else:
            order_by = 'account_move_line.date_maturity ASC, account_move_line.date ASC, account_move_line.id ASC'

        sub_queries = [
            r'''(
                SUBSTRING(REGEXP_REPLACE(LOWER(%s), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*')
                ~ SUBSTRING(REGEXP_REPLACE(LOWER(batch.name), '[^0-9a-z\s]', '', 'g'), '\S(?:.*\S)*')
            )'''
        ] * len(st_line_text_values)

        aml_domain = self._get_invoice_matching_amls_domain(st_line, partner)
        query = self.env['account.move.line']._where_calc(aml_domain)
        tables, where_clause, where_params = query.get_sql()

        self._cr.execute(
            f'''
                SELECT account_move_line.id
                FROM {tables}
                JOIN account_payment pay ON pay.id = account_move_line.payment_id
                JOIN account_batch_payment batch ON batch.id = pay.batch_payment_id
                WHERE {where_clause}
                    AND batch.name IS NOT NULL
                    AND (''' + ' OR '.join(sub_queries) + f''')
                ORDER BY {order_by}
            ''',
            where_params + st_line_text_values,
        )
        candidate_ids = [r[0] for r in self._cr.fetchall()]
        if candidate_ids:
            return {
                'allow_auto_reconcile': True,
                'amls': self.env['account.move.line'].browse(candidate_ids),
            }

    def _get_invoice_matching_rules_map(self):
        # EXTENDS account
        res = super()._get_invoice_matching_rules_map()
        res[0].append(self._get_invoice_matching_batch_payments_candidates)
        return res
