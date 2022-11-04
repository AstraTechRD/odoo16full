# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import fields, models, tools, _
from odoo.exceptions import UserError


class LuxembourgishTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_lu.tax.report.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Luxembourgish Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).append(
            {'name': _('XML'), 'sequence': 30, 'action': 'open_report_export_wizard', 'file_export_type': _('XML')}
        )

    def get_tax_electronic_report_values(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        lu_template_values = self.env['l10n_lu.report.handler'].get_electronic_report_values(options)
        lines = report._get_lines({'unfold_all': True, **options})
        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))

        # When user selects custom dates, if its start and end date fall in the same month,
        # the report declaration will be considered monthly. If both dates fall in the same quarter,
        # it will be considered quarterly report. If both datas fall in different quarters,
        # it will be considered a yearly report.
        date_from_quarter = tools.date_utils.get_quarter_number(date_from)
        date_to_quarter = tools.date_utils.get_quarter_number(date_to)
        if date_from.month == date_to.month:
            period = date_from.month
            declaration_type = 'TVA_DECM'
        elif date_from_quarter == date_to_quarter:
            period = date_from_quarter
            declaration_type = 'TVA_DECT'
        elif date_from_quarter == 1 and date_to_quarter == 4:
            period = 1
            declaration_type = 'TVA_DECA'
        else:
            raise UserError(_('The selected period is not supported for the selected declaration type.'))

        values = {}
        for line in lines:
            # tax report's `code` would contain alpha-numeric string like `LUTAX_XXX` where characters
            # at last three positions will be digits, hence we split `code` with ` - ` and build dictionary
            # having `code` as dictionary key
            if len(report._parse_line_id(line.get('id'))) == 1:
                continue
            split_line_code = line.get('name', '').split(' - ')[0]
            if split_line_code and split_line_code.isdigit():
                balance = "{:.2f}".format(line['columns'][0]['no_format']).replace('.', ',')
                values[split_line_code] = {'value': balance, 'field_type': 'number'}

        on_payment = self.env['account.tax'].search([
            ('company_id', 'in', report.get_report_company_ids(options)),
            ('tax_exigibility', '=', 'on_payment')
        ], limit=1)
        values['204'] = {'value': on_payment and '0' or '1', 'field_type': 'boolean'}
        values['205'] = {'value': on_payment and '1' or '0', 'field_type': 'boolean'}
        for code, field_type in (('403', 'number'), ('418', 'number'), ('453', 'number')):
            values[code] = {'value': 0, 'field_type': field_type}
        if declaration_type == 'TVA_DECA':
            for code, field_type in (('042', 'float'), ('416', 'float'), ('417', 'float'), ('451', 'float'), ('452', 'float')):
                values[code] = {'value': 0, 'field_type': field_type}

        lu_template_values.update({
            'forms': [{
                'declaration_type': declaration_type,
                'year': date_from.year,
                'period': period,
                'currency': self.env.company.currency_id.name,
                'field_values': values
            }]
        })
        return lu_template_values

    def export_tax_report_to_xml(self, options):
        self.env['l10n_lu.report.handler']._validate_ecdf_prefix()

        lu_template_values = self.get_tax_electronic_report_values(options)
        for form in lu_template_values['forms']:
            values = form["field_values"]
            ordered_values = {}
            for code in sorted(values.keys()):
                ordered_values[code] = values[code]
            form["field_values"] = ordered_values
        rendered_content = self.env['ir.qweb']._render('l10n_lu_reports.l10n_lu_electronic_report_template_1_1', lu_template_values, minimal_qcontext=True)
        content = "\n".join(re.split(r'\n\s*\n', rendered_content))  # Remove empty lines
        self.env['l10n_lu.report.handler']._validate_xml_content(content)

        return {
            'file_name': self.env['l10n_lu.report.handler'].get_report_filename(options) + '.xml',
            'file_content': "<?xml version='1.0' encoding='UTF-8'?>" + content,
            'file_type': 'xml',
        }

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report."""
        new_context = self.env.context.copy()
        new_context['report_generation_options'] = options
        new_context['report_generation_options']['report_id'] = options['report_id']
        return self.env['l10n_lu.generate.tax.report'].with_context(new_context).create({}).get_xml()
