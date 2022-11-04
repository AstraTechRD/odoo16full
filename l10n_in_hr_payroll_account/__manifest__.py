# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'India - Payroll with Accounting',
    'icon': '/l10n_in/static/description/icon.png',
    'category': 'Human Resources',
    'depends': ['l10n_in_hr_payroll', 'hr_payroll_account', 'l10n_in'],
    'description': """
Accounting Data for Indian Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'data':[
        'data/l10n_in_hr_payroll_account_data.xml',
    ],
    'license': 'OEEL-1',
}
