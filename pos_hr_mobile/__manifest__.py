# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Barcode in Mobile',
    'category': 'Human Resources/Barcode',
    'summary': 'POS Barcode scan in Mobile',
    'version': '1.0',
    'description': """ """,
    'depends': ['pos_hr', 'web_mobile'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale.assets': [
            'pos_hr_mobile/static/src/js/LoginScreenMobile.js',
            'pos_hr_mobile/static/src/scss/barcode_mobile.scss',
            'barcodes_mobile/static/src/scss/barcode_mobile.scss',
            'pos_hr_mobile/static/src/xml/**/*',
        ],
    }
}
