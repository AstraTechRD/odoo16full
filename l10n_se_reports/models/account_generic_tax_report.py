from odoo import models, _
from odoo.tools import float_repr
from lxml import etree
from lxml.objectify import fromstring


DOCTYPE = '<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www1.skatteverket.se/demoeskd/eSKDUpload_6p0.dtd">'


class AccountGenericTaxReport(models.Model):
    _inherit = 'account.report'
    def l10n_se_reports_tax_report_init_custom_options(self, options, previous_options=None):
        options.setdefault('buttons', []).extend((
            {'name': _('XML'), 'sequence': 30, 'action': 'file_export',
             'action_param': 'l10n_se_export_tax_report_to_xml', 'file_export_type': _('XML')},
            {'name': _('Closing Entry'), 'action': 'action_periodic_vat_entries', 'sequence': 80},
        ))

    def l10n_se_export_tax_report_to_xml(self, options):
        report_lines = self._get_lines(options)
        export_template = 'l10n_se_reports.tax_export_xml'
        colname_to_idx = {col['name']: idx for idx, col in enumerate(options.get('columns', []))}
        lines_mapping = {
            line['columns'][colname_to_idx['Balance']]['report_line_id']: float_repr(line['columns'][colname_to_idx['Balance']]['no_format'], 0) for line in report_lines
        }
        template_context = {}
        for record in self.env['account.report.line'].browse(lines_mapping.keys()):
            template_context[record.code] = lines_mapping[record.id]
        template_context['org_number'] = self._get_sender_company_for_export(options).org_number
        template_context['period'] = (options['date']['date_to'][:4] + options['date']['date_to'][5:7])
        template_context['comment'] = ''

        qweb = self.env['ir.qweb']
        doc = qweb._render(export_template, values=template_context)
        tree = fromstring(doc)

        return {
            'file_name': self.get_default_report_filename('xml'),
            'file_content': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='ISO-8859-1', doctype=DOCTYPE),
            'file_type': 'xml',
        }
