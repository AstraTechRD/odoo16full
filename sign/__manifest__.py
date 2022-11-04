# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sign',
    'version': '1.0',
    'category': 'Sales/Sign',
    'sequence': 105,
    'summary': "Send documents to sign online and handle filled copies",
    'description': """
Sign and complete your documents easily. Customize your documents with text and signature fields and send them to your recipients.\n
Let your customers follow the signature process easily.
    """,
    'website': 'https://www.odoo.com/app/sign',
    'depends': ['mail', 'attachment_indexation', 'portal', 'sms'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'data/mail_templates.xml',
        'data/sign_data.xml',
        'views/sign_template_views_mobile.xml',
        'wizard/sign_duplicate_template_with_pdf_views.xml',
        'wizard/sign_send_request_views.xml',
        'views/sign_request_templates.xml',
        'views/sign_template_templates.xml',
        'views/sign_request_views.xml',
        'views/sign_template_views.xml',
        'views/sign_log_views.xml',
        'views/sign_portal_templates.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/sign_pdf_iframe_templates.xml',
        'views/terms_views.xml',
        'report/sign_log_reports.xml',
        'report/green_saving_reports.xml'
    ],
    'demo': [
        'data/sign_demo.xml',
    ],
    'application': True,
    'post_init_hook': '_sign_post_init',
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'mail.assets_messaging': [
            'sign/static/src/models/*.js',
        ],
        'sign.assets_pdf_iframe': [
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/jquery.ui/jquery-ui.css',
            'web/static/lib/select2/select2.css',
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/vendor/_rfs.scss',
            'web/static/lib/bootstrap/scss/mixins/_deprecate.scss',
            'web/static/lib/bootstrap/scss/mixins/_utilities.scss',
            'web/static/lib/bootstrap/scss/mixins/_breakpoints.scss',
            'web/static/lib/bootstrap/scss/mixins/_grid.scss',
            'web/static/lib/bootstrap/scss/_utilities.scss',
            'web/static/lib/bootstrap/scss/_grid.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/legacy/scss/utils.scss',
            'web/static/src/scss/primary_variables.scss',
            'web_enterprise/static/src/scss/primary_variables.scss',
            'web_tour/static/src/scss/tip.scss',
            'sign/static/src/css/iframe.css',
            'web/static/src/scss/secondary_variables.scss',
            'sign/static/src/scss/iframe.scss',
        ],
        'sign.assets_green_report': [
            'sign/report/green_saving_reports.scss'
        ],
        'web.assets_common': [
            'sign/static/src/js/common/*',
            'sign/static/src/xml/sign_common.xml',
            'sign/static/src/xml/sign_modal.xml',
            'sign/static/src/scss/sign_common.scss',
            'web_editor/static/lib/html2canvas.js',
        ],
        'web.assets_backend': [
            'sign/static/src/js/backend/*',
            'sign/static/src/js/tours/sign.js',
            'sign/static/src/js/activity.js',
            'sign/static/src/scss/sign_backend.scss',
            'sign/static/src/xml/*.xml',
            'sign/static/src/components/**/*',
            'sign/static/src/views/**/*',
        ],
        'web.assets_frontend': [
            'sign/static/src/js/common/*',
            'sign/static/src/xml/sign_common.xml',
            'sign/static/src/xml/sign_modal.xml',
            'sign/static/src/scss/sign_common.scss',
            'web_editor/static/lib/html2canvas.js', # FIXME this should definitely not be in assets_frontend and be lazy loaded only when needed
            'sign/static/src/scss/sign_frontend.scss',
        ],
        'web.assets_tests': [
            'sign/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'sign/static/tests/document_backend_tests.js',
        ],
    }
}
