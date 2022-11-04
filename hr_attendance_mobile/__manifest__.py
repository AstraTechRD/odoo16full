# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Attendances Barcode in Mobile',
    'category': 'Human Resources/Attendances',
    'summary': 'Attendances Barcode scan in Mobile',
    'version': '1.0',
    'description': """ """,
    'depends': ['hr_attendance', 'barcodes_mobile'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'hr_attendance_mobile/static/src/js/**/*',
            'hr_attendance_mobile/static/src/xml/**/*',
        ],
    }
}
