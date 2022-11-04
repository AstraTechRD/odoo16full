# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Accounting',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Invoices from Documents',
    'description': """
Bridge module between the accounting and documents apps. It enables
the creation invoices from the Documents module, and adds a
button on Accounting's reports allowing to save the report into the
Documents app in the desired format(s).
""",
    'website': ' ',
    'depends': ['documents', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/data.xml',
        'data/mail_activity_type_data.xml',
        'views/documents_views.xml',
        'views/account_move_views.xml',
        'wizard/report_export_wizard.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'documents_account/static/**/*',
        ],
    }
}
