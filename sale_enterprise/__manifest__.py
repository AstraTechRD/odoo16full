# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale enterprise",
    'version': "1.0",
    'category': "Sales/Sales",
    'summary': "Advanced Features for Sale Management",
    'description': """
Contains advanced features for sale management
    """,
    'depends': ['sale'],
    'data': [
        'report/sale_report_views.xml',
    ],
    'installable': True,
    'auto_install': ['sale'],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'sale_enterprise/static/**/*',
        ],
    }
}
