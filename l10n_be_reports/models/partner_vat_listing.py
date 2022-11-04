# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError
from markupsafe import Markup
from itertools import groupby
from .account_report import _raw_phonenumber, _get_xml_export_representative_node


class PartnerVATListingCustomHandler(models.AbstractModel):
    _name = 'l10n_be.partner.vat.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Partner VAT Listing Custom Handler'

    def _caret_options_initializer(self):
        return {
            'res.partner': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
                {'name': _("Audit"), 'action': 'partner_vat_listing_open_invoices'},
            ]
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        operations_tags_expr = [
            'l10n_be.tax_report_line_00_tag', 'l10n_be.tax_report_line_01_tag', 'l10n_be.tax_report_line_02_tag',
            'l10n_be.tax_report_line_03_tag', 'l10n_be.tax_report_line_45_tag', 'l10n_be.tax_report_line_49_tag',
        ]

        operation_expressions = self.env['account.report.expression']

        for xmlid in operations_tags_expr:
            operation_expressions += self.env.ref(xmlid)

        options['partner_vat_listing_operations_tag_ids'] = operation_expressions._get_matching_tags().ids

        taxes_tags_expr = ['l10n_be.tax_report_line_54_tag', 'l10n_be.tax_report_line_64_tag']
        tax_expressions = self.env['account.report.expression']

        for xmlid in taxes_tags_expr:
            tax_expressions += self.env.ref(xmlid)

        options['partner_vat_listing_taxes_tag_ids'] = tax_expressions._get_matching_tags().ids

        options['buttons'] += [{
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'partner_vat_listing_export_to_xml',
            'file_export_type': _('XML')
        }]

    def _report_custom_engine_partner_vat_listing(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        def build_result_dict(query_res_lines):
            if current_groupby:
                rslt = {
                    'vat_number': query_res_lines[0]['vat'],
                    'turnover': query_res_lines[0]['turnover'],
                    'vat_amount': query_res_lines[0]['vat_amount'],
                    'has_sublines': False,
                }
            else:
                turnover = 0.0
                vat_amount = 0.0

                for line in enumerate(query_res_lines):
                    turnover += line[1]['turnover']
                    vat_amount += line[1]['vat_amount']

                rslt = {
                    'vat_number': None,
                    'turnover': turnover,
                    'vat_amount': vat_amount,
                    'has_sublines': False,
                }

            return rslt

        report = self.env.ref('l10n_be_reports.l10n_be_partner_vat_listing')
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        if current_groupby == 'id':
            raise UserError(_('Grouping by ID key is not supported by partner VAT custom engine.'))

        partner_ids = self.env['res.partner'].with_context(active_test=False).search([('vat', 'ilike', 'BE%')]).ids

        if not partner_ids:
            return []

        tables, where_clause, where_params = report._query_get(options, 'strict_range')

        query = f'''
            SELECT
                {'turnover_sub.grouping_key,refund_vat_sub.grouping_key,refund_base_sub.grouping_key,' if current_groupby else ''}
                turnover_sub.partner_id, turnover_sub.name, turnover_sub.vat, turnover_sub.turnover,
                refund_vat_sub.refund_base,
                refund_base_sub.vat_amount, refund_base_sub.refund_vat_amount
            FROM (
                -- Turnover --
                SELECT
                    {f'"account_move_line".{current_groupby} AS grouping_key,' if current_groupby else ''}
                    "account_move_line".partner_id, p.name, p.vat,
                    SUM("account_move_line".credit - "account_move_line".debit) AS turnover
                FROM {tables}
                LEFT JOIN res_partner p
                    ON "account_move_line".partner_id = p.id
                JOIN account_account_tag_account_move_line_rel aml_tag
                    ON "account_move_line".id = aml_tag.account_move_line_id
                LEFT JOIN account_move inv
                    ON "account_move_line".move_id = inv.id
                WHERE
                    p.vat IS NOT NULL
                    AND aml_tag.account_account_tag_id IN %s
                    AND "account_move_line".partner_id IN %s
                    AND (
                        ("account_move_line".move_id IS NULL AND "account_move_line".credit > 0)
                        OR (inv.move_type IN ('out_refund', 'out_invoice') AND inv.state = 'posted')
                    )
                    AND {where_clause}
                GROUP BY
                    {f'"account_move_line".{current_groupby},' if current_groupby else ''}
                    "account_move_line".partner_id, p.name, p.vat
            ) AS turnover_sub

            FULL JOIN (
                -- Refund vat --
                SELECT
                    {f'"account_move_line".{current_groupby} AS grouping_key,' if current_groupby else ''}
                    "account_move_line".partner_id,
                    SUM("account_move_line".debit - "account_move_line".credit) AS refund_base
                FROM {tables}
                JOIN res_partner p
                    ON "account_move_line".partner_id = p.id
                JOIN account_account_tag_account_move_line_rel aml_tag
                    ON "account_move_line".id = aml_tag.account_move_line_id
                LEFT JOIN account_move inv
                    ON "account_move_line".move_id = inv.id
                WHERE
                    p.vat IS NOT NULL
                    AND aml_tag.account_account_tag_id IN %s
                    AND "account_move_line".partner_id IN %s
                    AND (
                        ("account_move_line".move_id IS NULL AND "account_move_line".credit > 0)
                        OR (inv.move_type = 'out_refund' AND inv.state = 'posted')
                    )
                    AND {where_clause}
                GROUP BY
                    {f'"account_move_line".{current_groupby},' if current_groupby else ''}
                    "account_move_line".partner_id, p.name, p.vat
            ) AS refund_vat_sub
            ON turnover_sub.partner_id = refund_vat_sub.partner_id
            {'AND turnover_sub.grouping_key = refund_vat_sub.grouping_key' if current_groupby  else ''}

            LEFT JOIN (
                -- Refund base
                SELECT
                    {f'"account_move_line".{current_groupby} AS grouping_key,' if current_groupby else ''}
                    COALESCE("account_move_line".partner_id, inv.partner_id) AS partner_id,
                    SUM("account_move_line".credit - "account_move_line".debit) AS vat_amount,
                    SUM("account_move_line".debit) AS refund_vat_amount
                FROM {tables}
                JOIN account_account_tag_account_move_line_rel aml_tag2
                    ON "account_move_line".id = aml_tag2.account_move_line_id
                LEFT JOIN account_move inv
                    ON "account_move_line".move_id = inv.id
                WHERE
                    aml_tag2.account_account_tag_id IN %s
                    AND COALESCE("account_move_line".partner_id, inv.partner_id) IN %s
                    AND (
                        ("account_move_line".move_id IS NULL AND "account_move_line".credit > 0)
                        OR (inv.move_type IN ('out_refund', 'out_invoice') AND inv.state = 'posted')
                    )
                    AND {where_clause}
                GROUP BY
                    {f'"account_move_line".{current_groupby},' if current_groupby else ''}
                    COALESCE("account_move_line".partner_id, inv.partner_id)
            ) AS refund_base_sub
            ON turnover_sub.partner_id = refund_base_sub.partner_id
            {'AND turnover_sub.grouping_key = refund_base_sub.grouping_key' if current_groupby  else ''}

            WHERE turnover > 250 OR refund_base > 0 OR refund_vat_amount > 0
            ORDER BY turnover_sub.vat, turnover_sub.turnover DESC
        '''

        params = [
            tuple(options['partner_vat_listing_operations_tag_ids']), tuple(partner_ids), *where_params,
            tuple(options['partner_vat_listing_operations_tag_ids']), tuple(partner_ids), *where_params,
            tuple(options['partner_vat_listing_taxes_tag_ids']), tuple(partner_ids), *where_params,
        ]

        self._cr.execute(query, params)

        if not current_groupby:
            return build_result_dict(self._cr.dictfetchall())
        else:
            rslt = []
            all_res_per_grouping_key = {}

            for query_res in self._cr.dictfetchall():
                grouping_key = query_res.get('grouping_key')
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(query_res_lines)))

            return rslt

    def partner_vat_listing_open_invoices(self, options, params=None):
        domain = [
            ('move_id.move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
            ('move_id.date', '>=', options['date']['date_from']),
            ('move_id.date', '<=', options['date']['date_to']),
        ]

        # This action can also be called from the EC Sales Report.
        # In that case, we don't want to restrict the partner's VAT or 'tax_tag_ids'.
        if self == self.env.ref('l10n_be_reports.l10n_be_partner_vat_listing'):
            domain += [
                ('move_id.partner_id.vat', 'ilike', 'BE%'),
                ('tax_tag_ids', 'in', options['partner_vat_listing_operations_tag_ids'] + options['partner_vat_listing_taxes_tag_ids']),
            ]

        return {
            'name': _('VAT Listing Audit'),
            'type': 'ir.actions.act_window',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list'], [False, 'form']],
            'res_model': 'account.move.line',
            'context': {
                'search_default_partner_id': self.env['account.report']._get_model_info_from_id(params['line_id'])[1],
                'search_default_group_by_partner': 1,
                'expand': 1,
            },
            'domain': domain,
        }

    def partner_vat_listing_export_to_xml(self, options):
        # Precheck
        company = self.env.company
        company_vat = company.partner_id.vat
        report = self.env['account.report'].browse(options['report_id'])

        if not company_vat:
            raise UserError(_('No VAT number associated with your company.'))

        default_address = company.partner_id.address_get()
        address = default_address.get('invoice', company.partner_id)

        if not address.email:
            raise UserError(_('No email address associated with the company.'))

        if not address.phone:
            raise UserError(_('No phone associated with the company.'))

        # Write xml
        seq_declarantnum = self.env['ir.sequence'].next_by_code('declarantnum')
        company_vat = company_vat.replace(' ', '').upper()
        SenderId = company_vat[2:]
        issued_by = company_vat[:2]
        dnum = company_vat[2:] + seq_declarantnum[-4:]
        street = city = country = ''
        addr = company.partner_id.address_get(['invoice'])

        if addr.get('invoice', False):
            addr_partner = self.env['res.partner'].browse([addr['invoice']])
            phone = addr_partner.phone and _raw_phonenumber(addr_partner.phone) or address.phone and _raw_phonenumber(address.phone)
            email = addr_partner.email or ''
            city = addr_partner.city or ''
            zip_code = addr_partner.zip or ''

            if not city:
                city = ''
            if addr_partner.street:
                street = addr_partner.street
            if addr_partner.street2:
                street += ' ' + addr_partner.street2
            if addr_partner.country_id:
                country = addr_partner.country_id.code

        # Turnover and Farmer tags are not included
        options['date']['date_from'] = options['date']['date_from'][0:4] + '-01-01'
        options['date']['date_to'] = options['date']['date_to'][0:4] + '-12-31'
        lines = report._get_lines(options)

        data_client_info = ''
        seq = 0
        sum_turnover = 0.00
        sum_tax = 0.00

        for vat_number, values in groupby(lines[1:], key=lambda line: line['columns'][0]['name']):
            turnover = 0.0
            vat_amount = 0.0

            for value in list(values):
                line_model = report._get_model_info_from_id(value['id'])[0]

                if line_model != 'res.partner':
                    continue

                for column in value['columns']:
                    col_expr_label = column['expression_label']

                    if col_expr_label == 'turnover':
                        turnover += column['no_format'] or 0.0
                    elif col_expr_label == 'vat_amount':
                        vat_amount += column['no_format'] or 0.0

            seq += 1
            sum_turnover += turnover
            sum_tax += vat_amount
            amount_data = {
                'seq': str(seq),
                'only_vat': vat_number[2:],
                'turnover': turnover,
                'vat_amount': vat_amount,
            }
            data_client_info += Markup("""
        <ns2:Client SequenceNumber="%(seq)s">
            <ns2:CompanyVATNumber issuedBy="BE">%(only_vat)s</ns2:CompanyVATNumber>
            <ns2:TurnOver>%(turnover).2f</ns2:TurnOver>
            <ns2:VATAmount>%(vat_amount).2f</ns2:VATAmount>
        </ns2:Client>""") % amount_data

        annual_listing_data = {
            'issued_by': issued_by,
            'company_vat': company_vat,
            'comp_name': company.name,
            'street': street,
            'zip_code': zip_code,
            'city': city,
            'country': country,
            'email': email,
            'phone': phone,
            'SenderId': SenderId,
            'period': options['date'].get('date_from')[0:4],
            'comments': report._get_report_manager(options).summary or '',
            'seq': str(seq),
            'dnum': dnum,
            'sum_turnover': sum_turnover,
            'sum_tax': sum_tax,
            'representative_node': _get_xml_export_representative_node(report),
        }

        data_begin = Markup("""<?xml version="1.0" encoding="ISO-8859-1"?>
<ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
    <ns2:ClientListing SequenceNumber="1" ClientsNbr="%(seq)s" DeclarantReference="%(dnum)s"
        TurnOverSum="%(sum_turnover).2f" VATAmountSum="%(sum_tax).2f">
        %(representative_node)s
        <ns2:Declarant>
            <VATNumber>%(SenderId)s</VATNumber>
            <Name>%(comp_name)s</Name>
            <Street>%(street)s</Street>
            <PostCode>%(zip_code)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>%(period)s</ns2:Period>""") % annual_listing_data

        data_end = Markup("""
        <ns2:Comment>%(comments)s</ns2:Comment>
    </ns2:ClientListing>
</ns2:ClientListingConsignment>""") % annual_listing_data

        return {
            'file_name': report.get_default_report_filename('xml'),
            'file_content': (data_begin + data_client_info + data_end).encode('ISO-8859-1', 'ignore'),
            'file_type': 'xml',
        }
