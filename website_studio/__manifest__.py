# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Studio",
    'summary': "Display Website Elements in Studio",
    'description': """
Studio - Customize Odoo
=======================

This addon allows the user to display all the website forms linked to a certain
model. Furthermore, you can create a new website form or edit an existing one.

""",
    'category': 'Hidden',
    'version': '1.0',
    'depends': [
        'web_studio',
        'website',
    ],
    'data': [
        'views/templates.xml',
        'views/actions.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web_studio.studio_assets': [
            'website_studio/static/src/js/**/*.js',
            'website_studio/static/src/scss/**/*.scss',
            'website_studio/static/src/xml/*.xml',
        ],
        'web.qunit_suite_tests': [
            'website_studio/static/tests/**/*',
        ],
    }
}
