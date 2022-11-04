# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI v4.0 for Mexico',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Converts the Mexican EDI CFDI documents to version 4.0',
    'description': """
EDI CFDI 4.0
============
Convert CFDI XML documents to version 4.0 (from 3.3).
    """,
    'depends': [
        'l10n_mx_edi',
    ],
    'data': [
        'data/4.0/cfdi.xml',
        'data/4.0/payment20.xml',
        'data/account_edi_data.xml',
        'views/res_partner_view.xml',
    ],
    'demo': [
        'demo/res_partner.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
