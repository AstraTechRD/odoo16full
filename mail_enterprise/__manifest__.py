# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mail Enterprise',
    'category': 'Productivity/Discuss',
    'depends': ['mail', 'web_mobile'],
    'description': """
Bridge module for mail and enterprise
=====================================

Display a preview of the last chatter attachment in the form view for large
screen devices.
""",
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'mail.assets_messaging': [
            'mail_enterprise/static/src/models/*.js',
        ],
        'mail.assets_discuss_public': [
            'mail_enterprise/static/src/components/*/*',
            'web/static/src/core/action_swiper/*',
            'web_mobile/static/src/js/core/mixins.js',
            'web_mobile/static/src/js/core/session.js',
            'web_mobile/static/src/js/services/core.js',
        ],
        'web.assets_backend': [
            'mail_enterprise/static/src/components/*/*.js',
            'mail_enterprise/static/src/scss/mail_enterprise_mobile.scss',
            'mail_enterprise/static/src/widgets/*/*.js',
            'mail_enterprise/static/src/components/*/*.xml',
        ],
        'web.assets_tests': [
            'mail_enterprise/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'mail_enterprise/static/tests/qunit_suite_tests/**/*.js',
        ],
    }
}
