# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgium - Import SODA files',
    'icon': '/l10n_be/static/description/icon.png',
    'version': '1',
    'category': 'Accounting/Localizations',
    'description': '''
Module to import SODA files.
======================================
''',
    'depends': ['account_accountant', 'l10n_be'],
    'data': [
        'views/account_journal_dashboard_view.xml',
        'views/account_move_views.xml'
    ],
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'installable': True,
    'license': 'OEEL-1',
}
