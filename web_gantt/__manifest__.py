# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Gantt',
    'category': 'Hidden',
    'description': """
Odoo Web Gantt chart view.
=============================

    """,
    'version': '2.0',
    'depends': ['web'],
    'assets': {
        'web._assets_primary_variables': [
            'web_gantt/static/src/scss/web_gantt.variables.scss',
        ],
        'web.assets_backend': [
            'web_gantt/static/src/**/*',
            'web_gantt/static/src/xml/**/*',
        ],
        'web.qunit_suite_tests': [
            'web_gantt/static/tests/**/*',
            ('remove', 'web_gantt/static/tests/gantt_mobile_tests.js'),
        ],
        'web.qunit_mobile_suite_tests': [
            'web_gantt/static/tests/gantt_mobile_tests.js',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
