# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Studio",
    'summary': "Create and customize your Odoo apps",
    'website': 'https://www.odoo.com/app/studio',
    'description': """
Studio - Customize Odoo
=======================

This addon allows the user to customize most element of the user interface, in a
simple and graphical way. It has two main features:

* create a new application (add module, top level menu item, and default action)
* customize an existing application (edit menus, actions, views, translations, ...)

Note: Only the admin user is allowed to make those customizations.
""",
    'category': 'Customizations/Studio',
    'sequence': 75,
    'version': '1.0',
    'depends': [
        'base_automation',
        'base_import_module',
        'mail',
        'web',
        'web_enterprise',
        'web_editor',
        'web_map',
        'web_gantt',
        'sms',
    ],
    'data': [
        'views/assets.xml',
        'views/actions.xml',
        'views/base_import_module_view.xml',
        'views/ir_actions_report_xml.xml',
        'views/ir_model_data.xml',
        'views/studio_approval_views.xml',
        'data/mail_templates.xml',
        'data/mail_activity_type_data.xml',
        'wizard/base_module_uninstall_view.xml',
        'security/ir.model.access.csv',
        'security/studio_security.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'web_studio/static/src/systray_item/**/*.js',
            'web_studio/static/src/studio_service.js',
            'web_studio/static/src/utils.js',
            'web_studio/static/src/tours/**/*.js',

            'web_studio/static/src/legacy/js/approval_component.js',
            'web_studio/static/src/legacy/scss/approval_component.scss',
            'web_studio/static/src/legacy/js/bus.js',
            'web_studio/static/src/legacy/js/views/renderers/form_renderer.js',
            'web_studio/static/src/legacy/js/views/renderers/list_renderer_eager.js',
            'web_studio/static/src/legacy/js/views/controllers/form_controller.js',
            'web_studio/static/src/legacy/studio_legacy_service.js',
            'web_studio/static/src/home_menu/**/*.js',
            'web_studio/static/src/views/**/*.js',
            'web_studio/static/src/approval/**/*',
            'web_studio/static/src/**/*.xml',
            ('remove', 'web_studio/static/src/legacy/xml/sidebar_web_editor.xml'),
        ],
        'web_editor.assets_wysiwyg': {
            'web_studio/static/src/legacy/xml/sidebar_web_editor.xml',
        },
        'web.assets_backend_prod_only': [
            'web_studio/static/src/client_action/studio_action_loader.js',
            'web_studio/static/src/client_action/app_creator/app_creator_shortcut.js',
        ],
        # This bundle is lazy loaded: it is loaded when studio is opened for the first time
        'web_studio.studio_assets': [
            'web_studio/static/src/client_action/**/*.js',
            ('remove', 'web_studio/static/src/client_action/studio_action_loader.js'),
            ('remove', 'web_studio/static/src/client_action/app_creator/app_creator_shortcut.js'),
            'web_studio/static/src/legacy/action_editor_main.js',
            'web_studio/static/src/legacy/edit_menu_adapter.js',
            'web_studio/static/src/legacy/new_model_adapter.js',

            'web_studio/static/src/legacy/js/py.js',
            'web_studio/static/src/legacy/js/edit_menu.js',
            'web_studio/static/src/legacy/js/new_model.js',
            'web_studio/static/src/legacy/js/common_menu_dialog.js',
            'web_studio/static/src/legacy/js/common/**/*.js',
            'web_studio/static/src/legacy/js/reports/**/*.js',
            'web_studio/static/src/legacy/js/views/abstract_view.js',
            'web_studio/static/src/legacy/js/views/action_editor.js',
            'web_studio/static/src/legacy/js/views/action_editor_sidebar.js',
            'web_studio/static/src/legacy/js/views/action_editor_view.js',
            'web_studio/static/src/legacy/js/views/view_components.js',
            'web_studio/static/src/legacy/js/views/view_editor_manager.js',
            'web_studio/static/src/legacy/js/views/view_editor_sidebar.js',
            'web_studio/static/src/legacy/js/views/renderers/search_renderer.js',
            'web_studio/static/src/legacy/js/views/renderers/list_renderer_lazy.js',
            'web_studio/static/src/legacy/js/views/view_editors/**/*.js',

            ('include', 'web._assets_helpers'),
            'web_studio/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web_studio/static/src/client_action/variables.scss',
            'web_studio/static/src/client_action/mixins.scss',
            'web_studio/static/src/client_action/**/*.scss',

            'web_studio/static/src/legacy/scss/icons.scss',
            'web_studio/static/src/legacy/scss/action_editor.scss',
            'web_studio/static/src/legacy/scss/kanban_view.scss',
            'web_studio/static/src/legacy/scss/kanban_editor.scss',
            'web_studio/static/src/legacy/scss/list_editor.scss',
            'web_studio/static/src/legacy/scss/new_field_dialog.scss',
            'web_studio/static/src/legacy/scss/report_editor.scss',
            'web_studio/static/src/legacy/scss/report_editor_manager.scss',
            'web_studio/static/src/legacy/scss/report_editor_sidebar.scss',
            'web_studio/static/src/legacy/scss/report_kanban_view.scss',
            'web_studio/static/src/legacy/scss/search_editor.scss',
            'web_studio/static/src/legacy/scss/sidebar.scss',
            'web_studio/static/src/legacy/scss/view_editor_manager.scss',
            'web_studio/static/src/legacy/scss/xml_editor.scss',

            'web_studio/static/src/legacy/xml/new_model.xml',
        ],
        'web.assets_tests': [
            'web_studio/static/tests/legacy/tours/**/*',
        ],
        'web_studio.report_assets': [
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web_studio/static/src/legacy/scss/report_iframe.scss',
        ],
        'web.qunit_suite_tests': [
            # In tests we don't want to lazy load this
            # And we don't want to push them into any other test suite either
            # as web.tests_assets would
            ('include', 'web_studio.studio_assets'),
            'web_studio/static/tests/mock_server.js',
            'web_studio/static/tests/helpers.js',
            'web_studio/static/tests/*.js',
            'web_studio/static/tests/views/**/*.js',
            'web_studio/static/tests/legacy/action_editor_action_tests.js',
            'web_studio/static/tests/legacy/edit_menu_tests.js',
            'web_studio/static/tests/legacy/new_model_tests.js',
            'web_studio/static/tests/legacy/mock_server.js',
            'web_studio/static/tests/legacy/test_utils.js',
            'web_studio/static/tests/legacy/reports/**/*.js',
            'web_studio/static/tests/legacy/views/**/*.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'web_studio/static/tests/views/disable_patch.js',
        ],
    }
}
