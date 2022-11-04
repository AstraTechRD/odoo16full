# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, tools

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_nl_reports_load_xsd_files(self, force_reload=False):
        url = 'https://www.softwarepakketten.nl/upload/auditfiles/xaf/20140402_AuditfileFinancieelVersie_3_2.zip'
        xsd_name = 'XmlAuditfileFinancieel3.2.xsd'
        tools.load_xsd_files_from_url(self.env, url, 'xsd_nl_xaf_3.2.zip', force_reload=force_reload, xsd_names_filter=xsd_name)
        return

    @api.model
    def l10n_nl_reports_validate_xml_from_attachment(self, xml_content, xsd_name):
        return tools.validate_xml_from_attachment(self.env, xml_content, xsd_name, self._l10n_nl_reports_load_xsd_files)
