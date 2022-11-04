# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sign itsme',
    'version': '1.0',
    'category': 'Sales/Sign',
    'summary': "Sign documents with itsme® identification",
    'description': "Add support for itsme® identification when signing documents (Belgium and Netherlands only)",
    'depends': ['sign', 'iap'],
    'data': [
        'data/sign_itsme_data.xml',
        'report/sign_itsme_log_reports.xml',
        'views/sign_request_templates.xml'
    ],
    'assets': {
        'web.assets_common': [
            'sign_itsme/static/src/js/*',
            'sign_itsme/static/src/xml/*',
        ],
        'web.assets_frontend': [
            'sign_itsme/static/src/js/*',
            'sign_itsme/static/src/xml/*',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
