# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Payroll with Accounting',
    'icon': '/l10n_fr/static/description/icon.png',
    'category': 'Human Resources',
    'depends': ['l10n_fr_hr_payroll', 'hr_payroll_account', 'l10n_fr'],
    'description': """
Accounting Data for French Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'data':[
        'data/l10n_fr_hr_payroll_account_data.xml',
    ],
    'license': 'OEEL-1',
}
