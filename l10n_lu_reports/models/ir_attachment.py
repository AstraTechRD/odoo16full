# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_lu_reports_load_xsd_files(self, force_reload=False):
        url = 'https://ecdf-developer.b2g.etat.lu/ecdf/formdocs/eCDF_file_v2.0-XML_schema.xsd'
        xsd_name = 'xsd_lu_eCDF.xsd'

        def modify_xsd_content(content):
            return content.replace(b'<xsd:pattern value="[\\P{Cc}]+" />', b'')

        tools.load_xsd_files_from_url(self.env, url, xsd_name, force_reload=force_reload, modify_xsd_content=modify_xsd_content)
        return

    @api.model
    def l10n_lu_reports_validate_xml_from_attachment(self, xml_content, xsd_name):
        return tools.validate_xml_from_attachment(self.env, xml_content, xsd_name, self._l10n_lu_reports_load_xsd_files)
