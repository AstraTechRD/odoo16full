# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'IoT for restaurants',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Connect kitchen printers to your PoS',
    'description': """
Use receipt printers connected to an IoT Box to print orders in the kitchen or at the bar.
""",
    'data': ['views/restaurant_printer_views.xml',],
    'depends': ['pos_restaurant', 'iot'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale.assets': [
            'pos_restaurant_iot/static/**/*',
        ],
    }
}
