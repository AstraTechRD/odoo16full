# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Barcode in Mobile',
    'category': 'Hidden',
    'summary': 'Barcode scan in Mobile',
    'version': '1.0',
    'description': """ """,
    'depends': ['barcodes', 'web_mobile'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'barcodes_mobile/static/src/js/barcode_mobile_mixin.js',
            'barcodes_mobile/static/src/scss/barcode_mobile.scss',
            'barcodes_mobile/static/src/xml/**/*',
        ],
    }
}
