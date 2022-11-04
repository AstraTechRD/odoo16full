# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Belgian Payroll',
    'icon': '/l10n_be/static/description/icon.png',
    'category': 'Human Resources',
    'summary': 'Test Belgian Payroll',
    'depends': [
        'hr_contract_salary_payroll',
        'l10n_be_hr_contract_salary',
        'l10n_be_hr_payroll_account',
        'l10n_be',
        'account_accountant',
        'hr_payroll_account_sepa',
        'documents_hr_payroll',
        'documents_hr_recruitment',
        'documents_hr_contract',
        'hr_skills',
    ],
    'demo': ['data/test_l10n_be_hr_payroll_account_demo.xml'],
    'auto_install': True,
    'post_init_hook': '_generate_payslips',
    'assets': {
        'web.assets_tests': [
            'test_l10n_be_hr_payroll_account/static/tests/**/*',
        ],
    },
    'license': 'OEEL-1',
}
