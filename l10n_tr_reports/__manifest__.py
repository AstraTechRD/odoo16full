# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Turkey - Accounting Reports',
    'icon': '/l10n_tr/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
        Accounting reports for Turkey
    """,
    'depends': [
        'l10n_tr', 'account_reports'
    ],
    'data': [
        'data/account_financial_html_report_bilanco_data.xml',
        'data/account_financial_html_report_ozet_bilanco_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
