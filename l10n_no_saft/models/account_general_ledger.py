# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import base64
import re

from odoo import api, models, tools, _


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'NO':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_no_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def _l10n_no_prepare_saft_report_values(self, report, options):
        template_vals = report._saft_prepare_report_values(options)

        template_vals.update({
            'xmlns': 'urn:StandardAuditFile-Taxation-Financial:NO',
            'file_version': '1.10',
            'accounting_basis': 'A',
        })
        return template_vals

    @api.model
    def l10n_no_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_vals = self._l10n_no_prepare_saft_report_values(report, options)
        content = self.env['ir.qweb']._render('l10n_no_saft.saft_template_inherit_l10n_no_saft', template_vals)

        self.env['ir.attachment'].l10n_no_saft_validate_xml_from_attachment(content, 'xsd_no_saft.xsd')

        xsd_attachment = self.env['ir.attachment'].search([('name', '=', 'xsd_cached_Norwegian_SAF-T_Financial_Schema_v_1_10_xsd')])
        if xsd_attachment:
            with io.BytesIO(base64.b64decode(xsd_attachment.with_context(bin_size=False).datas)) as xsd:
                tools.xml_utils._check_with_xsd(content, xsd)
        return {
            'file_name': report.get_default_report_filename('xml'),
            'file_content': "\n".join(re.split(r'\n\s*\n', content)).encode(),
            'file_type': 'xml',
        }
