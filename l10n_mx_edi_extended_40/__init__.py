# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models

def _convert_external_trade(cr, registry):
    cr.execute("""
        UPDATE res_partner 
        SET l10n_mx_edi_external_trade_type = '02'
        WHERE l10n_mx_edi_external_trade = 't'
    """)
