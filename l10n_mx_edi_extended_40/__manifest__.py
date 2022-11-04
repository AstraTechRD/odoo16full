# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI v4.0 for Mexico (COMEX)',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Adds the CommercioExterior Complement to CFDI v4.0',
    'depends': [
        'l10n_mx_edi_40',
        'l10n_mx_edi_extended',
    ],
    'data': [
        'data/4.0/cfdi.xml',
        'data/4.0/payment20.xml',
        'views/account_move_view.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/res_partner.xml',

    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_convert_external_trade',
}
