# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': ' Electronic Delivery Guide for Mexico CFDI 4.0',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Support CFDI version 4.0',
    'depends': [
        'l10n_mx_edi_40',
        'l10n_mx_edi_stock',
    ],
    'data': [
        'data/cfdi_cartaporte.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
