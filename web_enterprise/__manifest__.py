# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Enterprise',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Enterprise Web Client.
===========================

This module modifies the web addon to provide Enterprise design and responsiveness.
        """,
    'depends': ['web'],
    'auto_install': True,
    'data': [
        'views/partner_view.xml',
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('after', 'web/static/src/scss/primary_variables.scss', 'web_enterprise/static/src/**/**/*.variables.scss'),
            ('before', 'web/static/src/scss/primary_variables.scss', 'web_enterprise/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('before', 'web/static/src/scss/secondary_variables.scss', 'web_enterprise/static/src/scss/secondary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('before', 'web/static/src/scss/bootstrap_overridden.scss', 'web_enterprise/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_common': [
            'web_enterprise/static/src/webclient/home_menu/home_menu_background.scss',
            'web_enterprise/static/src/webclient/navbar/navbar.scss',
        ],
        'web.assets_frontend': [
            'web_enterprise/static/src/webclient/home_menu/home_menu_background.scss',
            'web_enterprise/static/src/webclient/navbar/navbar.scss',
        ],
        'web.assets_backend': [
            ('replace', 'web/static/src/legacy/scss/fields_extra.scss', 'web_enterprise/static/src/legacy/scss/fields.scss'),
            ('replace', 'web/static/src/legacy/scss/form_view_extra.scss', 'web_enterprise/static/src/legacy/scss/form_view.scss'),
            ('replace', 'web/static/src/legacy/scss/list_view_extra.scss', 'web_enterprise/static/src/legacy/scss/list_view.scss'),

            'web_enterprise/static/src/legacy/scss/dropdown.scss',
            'web_enterprise/static/src/legacy/scss/control_panel_mobile.scss',
            'web_enterprise/static/src/legacy/scss/kanban_view.scss',
            'web_enterprise/static/src/legacy/scss/touch_device.scss',
            'web_enterprise/static/src/legacy/scss/form_view_mobile.scss',
            'web_enterprise/static/src/legacy/scss/modal_mobile.scss',
            'web_enterprise/static/src/legacy/scss/promote_studio.scss',
            'web_enterprise/static/src/webclient/**/*.scss',
            ('remove', 'web_enterprise/static/src/webclient/home_menu/home_menu_background.scss'), # already in _assets_common_styles
            ('remove', 'web_enterprise/static/src/webclient/navbar/navbar.scss'), # already in _assets_common_styles
            'web_enterprise/static/src/views/**/*.scss',

            # Allows events to be added to the ListRenderer before it is extended.
            # for more info, see: https://github.com/odoo/enterprise/pull/30169#pullrequestreview-1064657223
            ('prepend', 'web_enterprise/static/src/legacy/js/views/list/list_renderer_mobile.js'),

            'web_enterprise/static/src/legacy/js/apps.js',

            'web_enterprise/static/src/core/**/*',
            'web_enterprise/static/src/webclient/**/*.js',
            'web_enterprise/static/src/webclient/**/*.xml',
            'web_enterprise/static/src/views/**/*.js',
            'web_enterprise/static/src/views/**/*.xml',

            'web_enterprise/static/src/legacy/**/*.js',
            'web_enterprise/static/src/legacy/**/*.xml',

            # Don't include dark mode files in light mode
            ('remove', 'web_enterprise/static/src/**/**/*.dark.scss'),
        ],
        'web.assets_backend_prod_only': [
            ('replace', 'web/static/src/main.js', 'web_enterprise/static/src/main.js'),
        ],
        # ========= Dark Mode =========
        "web.dark_mode_variables": [
            # web._assets_primary_variables
            ('before', 'web_enterprise/static/src/scss/primary_variables.scss', 'web_enterprise/static/src/scss/primary_variables.dark.scss'),
            ('before', 'web_enterprise/static/src/**/**/*.variables.scss', 'web_enterprise/static/src/**/**/*.variables.dark.scss'),
            # web._assets_secondary_variables
            ('before', 'web_enterprise/static/src/scss/secondary_variables.scss', 'web_enterprise/static/src/scss/secondary_variables.dark.scss'),
        ],
        "web.dark_mode_assets_common": [
            ('include', 'web.dark_mode_variables'),
        ],
        "web.dark_mode_assets_backend": [
            ('include', 'web.dark_mode_variables'),
            # web._assets_backend_helpers
            ('before', 'web_enterprise/static/src/scss/bootstrap_overridden.scss', 'web_enterprise/static/src/scss/bootstrap_overridden.dark.scss'),
            ('after', 'web/static/lib/bootstrap/scss/_functions.scss', 'web_enterprise/static/src/scss/bs_functions_overridden.dark.scss'),
            # assets_backend
            'web_enterprise/static/src/**/**/*.dark.scss',
        ],
        'web.tests_assets': [
            'web_enterprise/static/tests/*.js',
        ],
        'web.qunit_suite_tests': [
            'web_enterprise/static/tests/views/**/*.js',
            'web_enterprise/static/tests/webclient/**/*.js',

            'web_enterprise/static/tests/legacy/views/list_tests.js',
            'web_enterprise/static/tests/legacy/barcodes_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'web_enterprise/static/tests/views/disable_patch.js',
            'web_enterprise/static/tests/mobile/**/*.js',

            'web_enterprise/static/tests/legacy/action_manager_mobile_tests.js',
            'web_enterprise/static/tests/legacy/control_panel_mobile_tests.js',
            'web_enterprise/static/tests/legacy/form_mobile_tests.js',
            'web_enterprise/static/tests/legacy/relational_fields_mobile_tests.js',
            'web_enterprise/static/tests/legacy/views/basic/basic_render_mobile_tests.js',
            'web_enterprise/static/tests/legacy/views/kanban_mobile_tests.js',
            'web_enterprise/static/tests/legacy/views/list_mobile_tests.js',
            'web_enterprise/static/tests/legacy/components/action_menus_mobile_tests.js',
            'web_enterprise/static/tests/legacy/barcodes_mobile_tests.js',
        ],
    },
    'license': 'OEEL-1',
}
