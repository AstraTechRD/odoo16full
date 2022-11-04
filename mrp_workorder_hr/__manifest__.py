# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Employees time registration on Work Orders",
    'category': "Hidden",
    'summary': 'Link module between Mrp II and HR employees',

    'description': """
This module allows Employees (and not users) to log in to a workorder using a barcode, a PIN number or both.
The actual till still requires one user but an unlimited number of employees can log on to that till and complete manufacturing tasks.
    """,

    'depends': ['mrp_workorder', 'hr_hourly_cost', 'hr'],

    'data': [
        'views/hr_employee_views.xml',
        'views/mrp_workorder_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_operation_views.xml',
    ],
    'installable': True,
    'auto_install': ['mrp_workorder', 'hr'],
    'assets': {
        'web.assets_backend': [
            'mrp_workorder_hr/static/src/**/*.js',
            'mrp_workorder_hr/static/src/**/*.scss',
            'mrp_workorder_hr/static/src/**/*.xml',
        ],
        'web.assets_tests': [
            'mrp_workorder_hr/static/tests/tours/**/*',
        ],
    },
    'license': 'OEEL-1',
}
