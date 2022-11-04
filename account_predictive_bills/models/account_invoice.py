# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from odoo import api, fields, models
import re

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @contextmanager
    def _get_edi_creation(self):
        with super()._get_edi_creation() as move:
            previous_lines = move.invoice_line_ids
            yield move
            for line in move.invoice_line_ids - previous_lines:
                line._onchange_name_predictive()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_predict_postgres_dictionary(self):
        lang = self._context.get('lang') and self._context.get('lang')[:2]
        return {'fr': 'french'}.get(lang, 'english')

    def _build_query(self, additional_domain=None):
        query = self.env['account.move.line']._where_calc([
            ('move_id.move_type', '=', self.move_id.move_type),
            ('move_id.state', '=', 'posted'),
            ('display_type', '=', 'product'),
            ('company_id', '=', self.move_id.journal_id.company_id.id or self.env.company.id),
        ] + (additional_domain or []))
        query.order = 'account_move_line__move_id.invoice_date DESC'
        query.limit = int(self.env["ir.config_parameter"].sudo().get_param(
            "account.bill.predict.history.limit",
            '10000',
        ))
        return query

    def _predicted_field(self, field, query=None, additional_queries=None):
        r"""Predict the most likely value based on the previous history.

        This method uses postgres tsvector in order to try to deduce a field of
        an invoice line based on the text entered into the name (description)
        field and the partner linked.
        We give some more weight to search with the same partner_id (roughly
        20%) in order to have better result
        We only limit the search on the previous 10000 entries, which according
        to our tests bore the best results. However this limit parameter is
        configurable by creating a config parameter with the key:
        account.bill.predict.history.limit

        For information, the tests were executed with a dataset of 40 000 bills
        from a live database, We split the dataset in 2, removing the 5000 most
        recent entries and we tried to use this method to guess the account of
        this validation set based on the previous entries.
        The result is roughly 90% of success.

        :param field (str): the sql column that has to be predicted.
            /!\ it is injected in the query without any checks.
        :param query (osv.Query): the query object on account.move.line that is
            used to do the ranking, containing the right domain, limit, etc. If
            it is omitted, a default query is used.
        :param additional_queries (list<str>): can be used in addition to the
            default query on account.move.line to fetch data coming from other
            tables, to have starting values for instance.
            /!\ it is injected in the query without any checks.
        """
        if not self.name or not self.partner_id:
            return False

        psql_lang = self._get_predict_postgres_dictionary()
        description = self.name + ' partnerid' + str(self.partner_id.id or '').replace('-', 'x')
        parsed_description = re.sub(r"[*&()|!':<>=%/~@,.;$\[\]]+", " ", description)
        parsed_description = ' | '.join(parsed_description.split())

        from_clause, where_clause, params = (query if query is not None else self._build_query()).get_sql()
        try:
            self.env.cr.execute(f"""
                WITH source AS ({'(' + ') UNION ALL ('.join([self.env.cr.mogrify(f'''
                    SELECT {field} AS prediction,
                           (
                               setweight(to_tsvector(%%(lang)s, account_move_line.name), 'B'))
                               || (setweight(to_tsvector(
                                   'simple',
                                   'partnerid' || replace(account_move_line.partner_id::text, '-', 'x')
                               ), 'A')
                           ) AS document
                      FROM {from_clause}
                     WHERE {where_clause}
                  GROUP BY account_move_line.id
                ''', params).decode()] + (additional_queries or [])) + ')'}
                ),

                ranking AS (
                    SELECT prediction, ts_rank(source.document, query_plain) AS rank
                      FROM source, to_tsquery(%(lang)s, %(description)s) query_plain
                     WHERE source.document @@ query_plain
                )

                SELECT prediction, MAX(rank) AS ranking, COUNT(*)
                  FROM ranking
              GROUP BY prediction
              ORDER BY ranking DESC, count DESC
            """, {
                'lang': psql_lang,
                'description': parsed_description,
                'company_id': self.move_id.journal_id.company_id.id or self.env.company.id,
            })
            result = self.env.cr.dictfetchone()
            if result:
                return result['prediction']
        except Exception:
            # In case there is an error while parsing the to_tsquery (wrong character for example)
            # We don't want to have a blocking traceback, instead return False
            _logger.exception('Error while predicting invoice line fields')
        return False

    def _predict_taxes(self):
        field = 'array_agg(account_move_line__tax_rel__tax_ids.id ORDER BY account_move_line__tax_rel__tax_ids.id)'
        query = self._build_query()
        query.left_join('account_move_line', 'id', 'account_move_line_account_tax_rel', 'account_move_line_id', 'tax_rel')
        query.left_join('account_move_line__tax_rel', 'account_tax_id', 'account_tax', 'id', 'tax_ids')
        query.add_where('account_move_line__tax_rel__tax_ids.active IS NOT FALSE')
        return self._predicted_field(field, query)

    def _predict_product(self):
        query = self._build_query(['|', ('product_id', '=', False), ('product_id.active', '=', True)])
        return self._predicted_field('account_move_line.product_id', query)

    def _predict_account(self):
        field = 'account_move_line.account_id'
        additional_queries = ["""
                SELECT id as account_id,
                       setweight(to_tsvector(%(lang)s, name), 'B') AS document
                  FROM account_account account
                 WHERE account.deprecated IS NOT TRUE
                   AND account.internal_group  = 'expense'
                   AND company_id = %(company_id)s
        """]
        if self.move_id.is_purchase_document(True):
            excluded_group = 'income'
        else:
            excluded_group = 'expense'
        query = self._build_query([
            ('account_id.deprecated', '=', False),
            ('account_id.internal_group', '!=', excluded_group),
        ])
        return self._predicted_field(field, query, additional_queries)

    @api.onchange('name')
    def _onchange_name_predictive(self):
        if self._context.get('account_predictive_bills_disable_prediction'):
            return

        enabled_types = ['in_invoice']
        if self.env['ir.config_parameter'].sudo().get_param('account_predictive_bills.activate_out_invoice'):
            enabled_types += ['out_invoice']

        if self.move_id.move_type in enabled_types and self.name and self.display_type == 'product':
            if not self.product_id:
                predicted_product_id = self._predict_product()
                if predicted_product_id and predicted_product_id != self.product_id.id:
                    name = self.name
                    self.product_id = predicted_product_id
                    self.name = name

            # Product may or may not have been set above, if it has been set, account and taxes are set too
            if not self.product_id:
                # Predict account.
                predicted_account_id = self._predict_account()
                if predicted_account_id and predicted_account_id != self.account_id.id:
                    self.account_id = predicted_account_id

                # Predict taxes
                predicted_tax_ids = self._predict_taxes()
                if predicted_tax_ids == [None]:
                    predicted_tax_ids = []
                if predicted_tax_ids is not False and set(predicted_tax_ids) != set(self.tax_ids.ids):
                    self.tax_ids = self.env['account.tax'].browse(predicted_tax_ids)
