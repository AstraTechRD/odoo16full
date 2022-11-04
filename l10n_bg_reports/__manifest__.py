# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting Reports',
    'icon': '/l10n_bg/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'author': 'Odoo S.A.',
    'description': """
        Base module for Bulgarian reports
    """,
    'depends': [
        'l10n_bg',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
