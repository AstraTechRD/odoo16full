# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "VOIP",

    'summary': """
        Make calls using a VOIP system""",

    'description': """
Allows to make call from next activities or with click-to-dial.
    """,

    'category': 'Productivity/VOIP',
    'sequence': 280,
    'version': '2.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'web', 'phone_validation', 'web_mobile'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/res_users_settings_views.xml',
        'views/voip_phonecall_views.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'mail.assets_messaging': [
            'voip/static/src/models/*.js',
        ],
        'web.assets_backend': [
            'voip/static/lib/sip.js',
            'voip/static/src/js/dialing_panel.js',
            'voip/static/src/js/phone_call.js',
            'voip/static/src/js/phone_call_activities_tab.js',
            'voip/static/src/js/phone_call_contacts_tab.js',
            'voip/static/src/js/phone_call_details.js',
            'voip/static/src/js/phone_call_recent_tab.js',
            'voip/static/src/js/phone_call_tab.js',
            'voip/static/src/js/phone_field.js',
            'voip/static/src/js/dialing_panel_container.js',
            'voip/static/src/js/voip_systray_item.js',
            'voip/static/src/js/legacy_compatibility.js',
            'voip/static/src/js/user_agent.js',
            'voip/static/src/scss/voip.scss',
            'voip/static/src/voip_service.js',
            'voip/static/src/components/*/*',
            'voip/static/src/xml/*.xml',
        ],
        'web.assets_backend_prod_only': [
            'voip/static/src/main.js',
        ],
        'web.tests_assets': [
            'voip/static/tests/helpers/*.js',
        ],
         "web.dark_mode_assets_backend": [
            'voip/static/src/scss/voip.dark.scss',
        ],
        'web.qunit_suite_tests': [
            'voip/static/tests/qunit_suite_tests/**/*.js',
        ],
    }
}
