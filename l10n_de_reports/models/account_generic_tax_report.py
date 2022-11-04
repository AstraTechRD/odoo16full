from odoo import models, fields, _
from odoo.tools import float_repr
from lxml import etree
from datetime import date, datetime


class GermanTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_de.tax.report.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'German Tax Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        # Overridden to prevent having unnecessary lines from the generic tax report.
        return []

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).extend((
            {
                'name': _('XML'),
                'sequence': 30,
                'action': 'export_file',
                'action_param': 'export_tax_report_to_xml',
                'file_export_type': _('XML'),
            },
            {
                'name': _('Closing Entry'),
                'action': 'action_periodic_vat_entries',
                'sequence': 80,
            },
        ))

    def export_tax_report_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_context = {}
        options = report._get_options(options)
        date_to = datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
        template_context['year'] = date_to.year
        if options['date']['period_type'] == 'month':
            template_context['period'] = date_to.strftime("%m")
        elif options['date']['period_type'] == 'quarter':
            month_end = int(date_to.month)
            if month_end % 3 != 0:
                raise ValueError('Quarter not supported')
            # For quarters, the period should be 41, 42, 43, 44 depending on the quarter.
            template_context['period'] = int(month_end / 3 + 40)
        template_context['creation_date'] = date.today().strftime("%Y%m%d")
        template_context['company'] = report._get_sender_company_for_export(options)

        qweb = self.env['ir.qweb']
        doc = qweb._render('l10n_de_reports.tax_export_xml', values=template_context)
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(doc, parser)

        taxes = tree.xpath('//Umsatzsteuervoranmeldung')[0]
        # Add the values dynamically. We do it here because the tag is generated from the code and
        # Qweb doesn't allow dynamically generated tags.
        elem = etree.SubElement(taxes, "Kz09")
        elem.text = "0.00" #please keep "0.00" until Odoo has "Kz09"

        report_lines = report._get_lines(options)
        colname_to_idx = {col['name']: idx for idx, col in enumerate(options.get('columns', []))}
        report_line_ids = [line['columns'][colname_to_idx['Balance']]['report_line_id'] for line in report_lines]
        codes_context = {}
        for record in self.env['account.report.line'].browse(report_line_ids):
            codes_context[record.id] = record.code

        for line in report_lines:
            line_code = codes_context[line['columns'][colname_to_idx['Balance']]['report_line_id']]
            if line_code and line_code.startswith('DE') and not line_code.endswith('BASE'):
                line_code = line_code.split('_')[1]
                #all "Kz" may be supplied as negative, except "Kz39"
                line_value = line['columns'][colname_to_idx['Balance']]['no_format']
                if line_value and (line_code != "39" or line_value > 0):
                    elem = etree.SubElement(taxes, "Kz" + line_code)
                    #only "kz09" and "kz83" can be supplied with decimals
                    if line_code in {"09", "83"}:
                        elem.text = float_repr(line_value, self.env.company.currency_id.decimal_places)
                    else:
                        elem.text = float_repr(int(line_value), 0)
                #"Kz09" and "kz83" must be supplied with 0.00 if they don't have balance
                elif line_code in {"09", "83"}:
                    elem = etree.SubElement(taxes, "Kz" + line_code)
                    elem.text = "0.00"

        return {
            'file_name': report.get_default_report_filename('xml'),
            'file_content': etree.tostring(tree, pretty_print=True, standalone=False, encoding='ISO-8859-1',),
            'file_type': 'xml',
        }
