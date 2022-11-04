# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for accounting",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'account_accountant'],
    'data': [
        "data/dashboards.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': ['account_accountant'],
    'license': 'OEEL-1',
    'assets': {}
}
