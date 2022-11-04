# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'eCommerce Subscription',
    'category': 'Hidden',
    'summary': 'Sell subscription products on your eCommerce',
    'version': '1.0',
    'description': """
This module allows you to sell subscription products in your eCommerce with
appropriate views and selling choices.
    """,
    'depends': ['website_sale', 'sale_subscription'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_subscription/static/src/js/*.js',
        ],
        'web.assets_tests': [
            'website_sale_subscription/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
