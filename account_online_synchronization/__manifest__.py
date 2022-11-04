# -*- coding: utf-8 -*-
{
    'name': "Online Bank Statement Synchronization",
    'summary': """
        This module is used for Online bank synchronization.""",

    'description': """
With this module, users will be able to link bank journals to their
online bank accounts (for supported banking institutions), and configure
a periodic and automatic synchronization of their bank statements.
    """,

    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account_accountant'],

    'data': [
        'data/config_parameter.xml',
        'data/mail_activity_type_data.xml',
        'security/ir.model.access.csv',
        'security/account_online_sync_security.xml',
        'views/account_online_sync.xml',
        'wizard/account_link_journal_wizard.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_online_synchronization/static/**/*',
        ],
    }
}
