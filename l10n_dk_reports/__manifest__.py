# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Denmark - Accounting Reports',
    'icon': '/l10n_dk/static/description/icon.png',
    'version': '1.0',
    'author': 'Odoo House ApS',
    'website': 'https://odoohouse.dk',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Denmark
=================================
    """,
    'depends': ['l10n_dk', 'account_reports'],
    'data': [
        'data/account_income_statement_html_report_data.xml',
        'data/account_balance_dk_html_report_data.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'auto_install': ['l10n_dk', 'account_reports'],
    'license': 'OEEL-1',
}
