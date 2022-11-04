# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Accounting Budget Sale Timesheet',
    'version': '1.0',
    'category': 'Account/budget/sale/timesheet',
    'summary': 'Accounting budget sale timesheet',
    'description': 'Bridge created to compute the planned amount of the budget items linked to the AA of a project',
    'depends': ['account_budget', 'sale_timesheet'],
    'data': [
        'views/project_update_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
