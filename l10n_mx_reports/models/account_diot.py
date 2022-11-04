# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import division

from contextlib import contextmanager
import locale
import re
import logging
from unicodedata import normalize


from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, get_lang

_logger = logging.getLogger(__name__)


class MexicanAccountReportCustomHandler(models.AbstractModel):
    _name = 'l10n_mx.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Mexican Account Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['columns'] = [column for column in options['columns']]
        options.setdefault('buttons', []).extend((
            {'name': _('DIOT (txt)'), 'sequence': 40, 'action': 'export_file', 'action_param': 'action_get_diot_txt', 'file_export_type': _('DIOT')},
            {'name': _('DPIVA (txt)'), 'sequence': 60, 'action': 'export_file', 'action_param': 'action_get_dpiva_txt', 'file_export_type': _('DPIVA')},
        ))

    def _report_custom_engine_diot_report(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        def build_dict(report, current_groupby, query_res):
            if not current_groupby:
                return query_res[0] if query_res else {k: None for k in report.mapped('line_ids.expression_ids.label')}
            return [(group_res["grouping_key"], group_res) for group_res in query_res]

        report = self.env['account.report'].browse(options['report_id'])
        query_res = self._execute_query(report, current_groupby, options, offset, limit)
        return build_dict(report, current_groupby, query_res)

    def _execute_query(self, report, current_groupby, options, offset, limit):
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        cash_basis_journal_ids = self.env.companies.filtered('tax_cash_basis_journal_id').tax_cash_basis_journal_id
        tables, where_clause, where_params = report._query_get(options, 'strict_range', domain=[
            ('parent_state', '=', 'posted'),
            ('journal_id', 'in', cash_basis_journal_ids.ids),
            ('move_id.reversal_move_id', '=', False),
            ('move_id.reversed_entry_id', '=', False),
        ])

        tag_16 = self.env.ref('l10n_mx.tag_diot_16')
        tag_16_non_cre = self.env.ref('l10n_mx.tag_diot_16_non_cre', raise_if_not_found=False) or self.env['account.account.tag']
        tag_8 = self.env.ref('l10n_mx.tag_diot_8', raise_if_not_found=False) or self.env['account.account.tag']
        tag_8_non_cre = self.env.ref('l10n_mx.tag_diot_8_non_cre', raise_if_not_found=False) or self.env['account.account.tag']
        tag_imp = self.env.ref('l10n_mx.tag_diot_16_imp')
        tag_0 = self.env.ref('l10n_mx.tag_diot_0')
        tag_exe = self.env.ref('l10n_mx.tag_diot_exento')
        tag_ret = self.env.ref('l10n_mx.tag_diot_ret')

        raw_results_select_list = []
        lang = self.env.user.lang or get_lang(self.env).code
        if current_groupby == 'partner_id':
            raw_results_select_list.append(f'''
                CASE
                   WHEN country.code = 'MX' THEN '04'
                   ELSE '05'
                END AS third_party_code,
                partner.l10n_mx_type_of_operation AS operation_type_code,
                partner.vat AS partner_vat_number,
                country.code AS country_code,
                COALESCE(country.demonym->>'{lang}', country.demonym->>'en_US') AS partner_nationality,
           ''')
        else:
            raw_results_select_list.append('''
                NULL AS third_party_code,
                NULL AS operation_type_code,
                NULL AS partner_vat_number,
                NULL AS country_code,
                NULL AS partner_nationality,
            ''')

        raw_results_select_list += [
            f'''
                CASE
                   WHEN tag.id = %s THEN account_move_line.debit
                   ELSE 0
                END AS {column_name},
            '''
            for column_name in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt')
        ]

        tail_query, tail_params = report._get_engine_query_tail(offset, limit)
        self._cr.execute(f"""
            WITH raw_results as (
                SELECT
                    {f'account_move_line.{current_groupby}' if current_groupby else 'NULL'} AS grouping_key,
                    {''.join(raw_results_select_list)}
                   CASE
                        WHEN tag.id = %s
                        THEN account_move_line.balance * -tax.amount / 100
                        ELSE 0
                   END AS withheld,
                   CASE
                        WHEN tag.id != %s
                        THEN account_move_line.credit
                        ELSE 0
                   END AS refunds
                FROM {tables}
                JOIN account_move AS move ON move.id = account_move_line.move_id
                JOIN account_account_tag_account_move_line_rel AS tag_aml_rel ON account_move_line.id = tag_aml_rel.account_move_line_id
                JOIN account_account_tag AS tag ON tag.id = tag_aml_rel.account_account_tag_id
                JOIN account_move_line_account_tax_rel AS aml_tax_rel ON account_move_line.id = aml_tax_rel.account_move_line_id
                JOIN account_tax AS tax ON tax.id = aml_tax_rel.account_tax_id
                JOIN res_partner AS partner ON partner.id = account_move_line.partner_id
                JOIN res_country AS country ON country.id = partner.country_id
                WHERE {where_clause}
                ORDER BY partner.name, account_move_line.date, account_move_line.id
            )
            SELECT
               raw_results.grouping_key AS grouping_key,
               count(raw_results.grouping_key) AS counter,
               raw_results.third_party_code AS third_party_code,
               raw_results.operation_type_code AS operation_type_code,
               COALESCE(raw_results.partner_vat_number, '') AS partner_vat_number,
               raw_results.country_code AS country_code,
               raw_results.partner_nationality AS partner_nationality,
               sum(raw_results.paid_16) AS paid_16,
               sum(raw_results.paid_16_non_cred) AS paid_16_non_cred,
               sum(raw_results.paid_8) AS paid_8,
               sum(raw_results.paid_8_non_cred) AS paid_8_non_cred,
               sum(raw_results.importation_16) AS importation_16,
               sum(raw_results.paid_0) AS paid_0,
               sum(raw_results.exempt) AS exempt,
               sum(raw_results.withheld) AS withheld,
               sum(raw_results.refunds) AS refunds
            FROM raw_results
            GROUP BY
                raw_results.grouping_key,
                raw_results.third_party_code,
                raw_results.operation_type_code,
                raw_results.partner_vat_number,
                raw_results.country_code,
                raw_results.partner_nationality
           {tail_query}
        """,
            [
                tag_16.id,
                tag_16_non_cre.id,
                tag_8.id,
                tag_8_non_cre.id,
                tag_imp.id,
                tag_0.id,
                tag_exe.id,
                tag_ret.id,
                tag_ret.id,
                *where_params,
                *tail_params,
            ],
        )
        return self.env.cr.dictfetchall()

    def action_get_diot_txt(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        partner_and_values_to_report = {
            p: v for p, v in self._get_diot_values_per_partner(report, options).items()
            # don't report those for which all amount are 0
            if sum([v[x] for x in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt', 'withheld', 'refunds')])
        }

        self.check_for_error_on_partner([partner for partner in partner_and_values_to_report])

        lines = []
        for partner, values in partner_and_values_to_report.items():
            if not sum([values[x] for x in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt', 'withheld', 'refunds')]):
                # don't report if there isn't any amount to report
                continue

            is_foreign_partner = values['third_party_code'] != '04'
            data = [''] * 25
            data[0] = values['third_party_code']  # Supplier Type
            data[1] = values['operation_type_code']  # Operation Type
            data[2] = values['partner_vat_number'] if not is_foreign_partner else '' # Tax Number
            data[3] = values['partner_vat_number'] if is_foreign_partner else ''  # Tax Number for Foreigners
            data[4] = ''.join(self.str_format(partner.name)).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else ''  # Name
            data[5] = values['country_code'] if is_foreign_partner else '' # Country
            data[6] = ''.join(self.str_format(values['partner_nationality'])).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else '' # Nationality
            data[7] = str(round(float(values['paid_16'])) or '')  # 16%
            data[9] = str(round(float(values['paid_16_non_cred'])) or '')  # 16% Non-Creditable
            data[12] = str(round(float(values['paid_8'])) or '')  # 8%
            data[14] = str(round(float(values['paid_8_non_cred'])) or '')  # 8% Non-Creditable
            data[15] = str(round(float(values['importation_16'])) or '')  # 16% - Importation
            data[20] = str(round(float(values['paid_0'])) or '')  # 0%
            data[21] = str(round(float(values['exempt'])) or '')  # Exempt
            data[22] = str(round(float(values['withheld'])) or '')  # Withheld
            data[23] = str(round(float(values['refunds'])) or '')  # Refunds

            lines.append('|'.join(str(d) for d in data))

        diot_txt_result = '\n'.join(lines)
        return {
            'file_name': report.get_default_report_filename('txt'),
            'file_content': diot_txt_result.encode(),
            'file_type': 'txt',
        }

    def action_get_dpiva_txt(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        partner_and_values_to_report = {
            p: v for p, v in self._get_diot_values_per_partner(report, options).items()
            # don't report those for which all amount are 0
            if sum([v[x] for x in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt', 'withheld', 'refunds')])
        }

        self.check_for_error_on_partner([partner for partner in partner_and_values_to_report])

        date = fields.datetime.strptime(options['date']['date_from'], DEFAULT_SERVER_DATE_FORMAT)
        with self._custom_setlocale():
            month = date.strftime("%B").capitalize()

        lines = []
        for partner, values in partner_and_values_to_report.items():
            if not sum([values[x] for x in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt', 'withheld', 'refunds')]):
                # don't report if there isn't any amount to report
                continue

            is_foreign_partner = values['third_party_code'] != '04'
            data = [''] * 48
            data[0] = '1.0'  # Version
            data[1] = f"{date.year}"  # Fiscal Year
            data[2] = 'MES'  # Cabling value
            data[3] = month  # Period
            data[4] = '1'  # 1 Because has data
            data[5] = '1'  # 1 = Normal, 2 = Complementary (Not supported now).
            data[8] = values['counter']  # Count the operations
            for num in range(9, 26):
                data[num] = '0'
            data[26] = values['third_party_code']  # Supplier Type
            data[27] = values['operation_type_code']  # Operation Type
            data[28] = values['partner_vat_number'] if not is_foreign_partner else ''  # Federal Taxpayer Registry Code
            data[29] = values['partner_vat_number'] if is_foreign_partner else ''  # Fiscal ID
            data[30] = ''.join(self.str_format(partner.name)).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else ''  # Name
            data[31] = values['country_code'] if is_foreign_partner else ''  # Country
            data[32] = ''.join(self.str_format(values['partner_nationality'])).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else ''  # Nationality
            data[33] = str(round(float(values['paid_16'])) or '')  # 16%
            data[36] = str(round(float(values['paid_8'])) or '')  # 8%
            data[39] = str(round(float(values['importation_16'])) or '')  # 16% - Importation
            data[44] = str(round(float(values['paid_0'])) or '')  # 0%
            data[45] = str(round(float(values['exempt'])) or '')  # Exempt
            data[46] = str(round(float(values['withheld'])) or '')  # Withheld
            data[47] = str(round(float(values['refunds'])) or '')  # Refunds

            lines.append('|{}|'.format('|'.join(str(d) for d in data)))

        dpiva_txt_result = '\n'.join(lines)
        return {
            'file_name': report.get_default_report_filename('txt'),
            'file_content': dpiva_txt_result.encode(),
            'file_type': 'txt',
        }

    def _get_diot_values_per_partner(self, report, options):
        options['unfolded_lines'] = {}  # This allows to only get the first groupby level: partner_id
        col_group_results = report._compute_expression_totals_for_each_column_group(report.line_ids.expression_ids, options, groupby_to_expand="partner_id")
        if len(col_group_results) != 1:
            raise UserError(_("You can only export one period at a time with this file format!"))
        expression_list = list(col_group_results.values())
        label_dict = {exp.label: v['value'] for d in expression_list for exp, v in d.items()}
        partner_to_label_val = {}
        for label, partner_to_value_list in label_dict.items():
            for partner_id, value in partner_to_value_list:
                partner_to_label_val.setdefault(self.env['res.partner'].browse(partner_id), {})[label] = value
        return partner_to_label_val

    def check_for_error_on_partner(self, partners):
        partner_missing_information = self.env['res.partner']
        for partner in partners:
            if partner.country_id.code == "MX" and not partner.vat:
                partner_missing_information += partner
            if not partner.l10n_mx_type_of_operation:
                partner_missing_information += partner

        if partner_missing_information:
            action_error = {
                'name': _('Partner missing informations'),
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'list',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', partner_missing_information.ids)],
            }
            msg = _('The report cannot be generated because some partners are missing a valid RFC or type of operation')
            raise RedirectWarning(msg, action_error, _("See the list of partners"))

    @staticmethod
    def str_format(text):
        if not text:
            return ''
        trans_tab = {
            ord(char): None for char in (
                u'\N{COMBINING GRAVE ACCENT}',
                u'\N{COMBINING ACUTE ACCENT}',
                u'\N{COMBINING DIAERESIS}',
            )
        }
        text_n = normalize('NFKC', normalize('NFKD', text).translate(trans_tab))
        check_re = re.compile(r'''[^A-Za-z\d Ññ]''')
        return check_re.sub('', text_n)

    @contextmanager
    def _custom_setlocale(self):
        old_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'es_MX.utf8')
        except locale.Error:
            _logger.info('Error when try to set locale "es_MX". Please contact your system administrator.')
        try:
            yield
        finally:
            locale.setlocale(locale.LC_TIME, old_locale)
