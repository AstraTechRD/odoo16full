# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo.tools import xml_utils
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_pe_edi_load_xsd_files(self, force_reload=False):
        url = 'http://cpe.sunat.gob.pe/sites/default/files/inline-files/XSD%202.1.zip'
        xsd_name = 'xsd_pe_edi.zip'

        def modify_xsd_content(content):
            return content.replace(b'schemaLocation="../common/', b'schemaLocation="')

        xml_utils.load_xsd_files_from_url(self.env, url, xsd_name, force_reload=force_reload, modify_xsd_content=modify_xsd_content)
        return

    @api.model
    def l10n_pe_edi_validate_xml_from_attachment(self, xml_content, xsd_name):
        return xml_utils.validate_xml_from_attachment(self.env, xml_content, xsd_name, self._l10n_pe_edi_load_xsd_files)

    def _l10n_pe_edi_check_with_xsd(self, xml_to_validate, validation_type):
        """
        This method validates the format description of the xml files

        :param xml_to_validate: xml to validate
        :param validation_type: the type of the document
        :return: empty string when file not found or XSD passes
         or the error when the XSD validation fails
        """
        validation_types = self._l10n_pe_edi_get_xsd_file_name()
        xsd_fname = validation_types[validation_type]
        try:
            self.l10n_pe_edi_validate_xml_from_attachment(xml_to_validate, xsd_fname)
            return ''
        except FileNotFoundError:
            _logger.info('The XSD validation files from Sunat has not been found, please run the cron manually. ')
            return ''
        except UserError as exc:
            return str(exc)

    def _l10n_pe_edi_get_xsd_file_name(self):
        return {
            '01': 'UBL-Invoice-2.1.xsd',
            '03': 'UBL-Invoice-2.1.xsd',
            '07': 'UBL-CreditNote-2.1.xsd',
            '08': 'UBL-DebitNote-2.1.xsd',
        }
