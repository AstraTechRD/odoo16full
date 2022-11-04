# -*- coding: utf-8 -*-
{
    'name': "Documents",

    'summary': "Document management",

    'description': """
        App to upload and manage your documents.
    """,

    'author': "Odoo",
    'category': 'Productivity/Documents',
    'sequence': 80,
    'version': '1.1',
    'application': True,
    'website': 'https://www.odoo.com/app/documents',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'portal', 'web_enterprise', 'attachment_indexation', 'digest'],

    # always loaded
    'data': [
        'data/ir_asset.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'data/mail_activity_type_data.xml',
        'data/documents_data.xml',
        'data/workflow_data.xml',
        'data/files_data.xml',
        'data/mail_template_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/documents_document_views.xml',
        'views/documents_facet_views.xml',
        'views/documents_folder_views.xml',
        'views/documents_share_views.xml',
        'views/documents_tag_views.xml',
        'views/documents_workflow_action_views.xml',
        'views/documents_workflow_rule_views.xml',
        'views/documents_menu_views.xml',
        'views/templates.xml',
        'views/mail_activity_views.xml',
        'wizard/documents_folder_deletion_wizard.xml',
        'wizard/request_activity_views.xml',
        'wizard/link_to_record_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'mail.assets_messaging': [
            'documents/static/src/models/*.js',
        ],
        'web.assets_backend': [
            'documents/static/src/scss/documents_views.scss',
            'documents/static/src/scss/documents_kanban_view.scss',
            'documents/static/src/views/**/*.js',
            'documents/static/src/views/**/*.scss',
            'documents/static/src/models/*.js',
            'documents/static/src/owl/components/pdf_manager/pdf_manager.js',
            'documents/static/src/owl/components/pdf_page/pdf_page.js',
            'documents/static/src/owl/components/pdf_group_name/pdf_group_name.js',
            'documents/static/src/js/tours/documents.js',
            'documents/static/src/owl/components/pdf_manager/pdf_manager.scss',
            'documents/static/src/owl/components/pdf_page/pdf_page.scss',
            'documents/static/src/owl/components/pdf_group_name/pdf_group_name.scss',
            'documents/static/src/components/*/*.xml',
            'documents/static/src/views/**/*.xml',
            'documents/static/src/owl/components/pdf_manager/pdf_manager.xml',
            'documents/static/src/owl/components/pdf_page/pdf_page.xml',
            'documents/static/src/owl/components/pdf_group_name/pdf_group_name.xml',
        ],
        'web._assets_primary_variables': [
            'documents/static/src/scss/documents.variables.scss',
        ],
        "web.dark_mode_variables": [
            ('before', 'documents/static/src/scss/documents.variables.scss', 'documents/static/src/scss/documents.variables.dark.scss'),
        ],
        'documents.public_page_assets': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'documents/static/src/scss/documents_public_pages.scss',
            'documents/static/src/js/documents_public_pages.js',
        ],
        'documents.pdf_js_assets': [
            ('include', 'web.pdf_js_lib'),
        ],
        'web.tests_assets': [
            'documents/static/tests/helpers/*',
            'documents/static/tests/legacy/helpers/*',
        ],
        'web.qunit_suite_tests': [
            'documents/static/tests/documents_test_utils.js',
            'documents/static/tests/documents_kanban_tests.js',
            'documents/static/tests/documents_pdf_manager_tests.js',
            'documents/static/tests/documents_systray_activity_menu_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'documents/static/tests/documents_test_utils.js',
            'documents/static/tests/documents_kanban_mobile_tests.js',
        ],
    }
}
