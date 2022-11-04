#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Payroll Accounting',
    'category': 'Human Resources/Payroll',
    'description': """
Generic Payroll system Integrated with Accounting.
==================================================

    * Expense Encoding
    * Payment Encoding
    * Company Contribution Management
    """,
    'depends': ['hr_payroll', 'account_accountant'],
    'data': [
        'data/hr_payroll_account_data.xml',
        'views/hr_payroll_account_views.xml',
        'report/hr_contract_history_report_views.xml',
    ],
    'demo': [
        'data/hr_payroll_account_demo.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
