{
    'name': 'Keypay Australian Payroll',
    'icon': '/l10n_au/static/description/icon.png',
    'version': '1.0',
    'summary': 'Australian Payroll using KeyPay Integration',
    'description': """
        KeyPay Payroll Integration
        This Module will synchronise all payrun journals from KeyPay to Odoo.
    """,
    'category': 'Accounting',
    'author': 'Odoo S.A.,Inspired Software Pty Limited',
    'contributors': [
        'Michael Villamar',
        'Jacob Oldfield',
    ],
    'website': 'http://www.inspiredsoftware.com.au',
    'depends': [
        'l10n_au',
        'account_accountant',
    ],
    'data': [
        'views/account_views.xml',
        'views/res_config_settings.xml',
        'data/ir_cron_data.xml',
    ],
    'test': ['../account/test/account_minimal_test.xml'],
    'installable': True,
    'license': 'OEEL-1',
}
