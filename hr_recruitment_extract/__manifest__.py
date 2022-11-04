# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hr Recruitment Extract',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Extract data from CV scans to fill application forms automatically',
    'depends': ['hr_recruitment', 'iap_mail', 'mail_enterprise'],
    'data': [
        'data/ir_cron_data.xml',
        'data/config_parameter_endpoint.xml',
        'data/ir_actions_server_data.xml',
        'views/hr_applicant_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
    }
}
