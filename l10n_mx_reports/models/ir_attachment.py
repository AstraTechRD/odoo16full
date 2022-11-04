# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_mx_reports_load_xsd_files(self, force_reload=False):
        url_1 = 'https://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas/CatalogoCuentas_1_3.xsd'
        xsd_name_1 = 'xsd_mx_cfdicoa_1_3.xsd'
        tools.load_xsd_files_from_url(self.env, url_1, xsd_name_1, force_reload=force_reload)

        url_2 = 'https://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion/BalanzaComprobacion_1_3.xsd'
        xsd_name_2 = 'xsd_mx_cfdibalance_1_3.xsd'
        tools.load_xsd_files_from_url(self.env, url_2, xsd_name_2, force_reload=force_reload)
        return

    @api.model
    def l10n_mx_reports_validate_xml_from_attachment(self, xml_content, xsd_name):
        return tools.validate_xml_from_attachment(self.env, xml_content, xsd_name, self._l10n_mx_reports_load_xsd_files)
