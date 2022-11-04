# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Subcontracting Studio",
    'summary': "Bridge module for MRP subcontracting and studio to avoid some conflicts",
    'description': "Bridge module for MRP subcontracting and studio",
    'category': 'Manufacturing/Manufacturing',
    'version': '1.0',
    'depends': ['mrp_subcontracting', 'web_studio'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'mrp_subcontracting.webclient': [
            ('remove', 'web_studio/static/src/legacy/studio_legacy_service.js'),
            ('remove', 'web_studio/static/src/studio_service.js'),
            ('remove', 'web_studio/static/src/views/list/list_renderer.js'),
        ],
    }
}
