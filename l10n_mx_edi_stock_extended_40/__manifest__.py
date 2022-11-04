# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Mexico - Electronic Delivery Guide Comex 4.0""",
    'version': '1.0.',
    'category': 'Accounting/Localizations/EDI',
    'description': """
    Bridge module to extend the delivery guide (Complemento XML Carta de Porte) for CFDI v4.0
    - exported goods (COMEX)
    - extended address fields
    """,
    'depends': [
        'l10n_mx_edi_stock_40',
        'l10n_mx_edi_stock_extended',
    ],
    'data': [
        'data/cfdi_cartaporte.xml',
        'views/product_views.xml',
        'views/vehicle_views.xml',
        'views/report_deliveryslip.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
    'license': 'OEEL-1',
}
