# -*- coding: utf-8 -*-
{
    'name': 'US - Accounting Reports',
    'icon': '/l10n_us/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
        Accounting reports for US
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends': [
        'l10n_us', 'account_reports'
    ],
    'data': [
        'data/account_financial_report_data.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_us', 'account_reports'],
    'license': 'OEEL-1',
}
