# -*- coding: utf-8 -*-

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _l10n_pe_edi_get_xsd_file_name(self):
        result = super()._l10n_pe_edi_get_xsd_file_name()
        result['09'] = 'UBL-StockPicking-2.1.xsd'
        return result
