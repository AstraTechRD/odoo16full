# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Subcontracting Enterprise",
    'summary': "Bridge module for MRP subcontracting and enterprise to avoid some conflicts with studio",
    'description': "Bridge module for MRP subcontracting and enterprise",
    'category': 'Manufacturing/Manufacturing',
    'version': '1.0',
    'depends': ['mrp_subcontracting'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'mrp_subcontracting.webclient': [
            ('remove', 'web_enterprise/static/src/webclient/home_menu/*.js'),
            ('remove', 'mrp_subcontracting/static/src/subcontracting_portal/main.js'),
            'mrp_subcontracting_enterprise/static/src/subcontracting_portal/remove_services.js',
            'mrp_subcontracting_enterprise/static/src/subcontracting_portal/main.js',
        ],
    }
}
