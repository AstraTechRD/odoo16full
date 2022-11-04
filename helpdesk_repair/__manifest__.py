# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Repair',
    'category': 'Services/Helpdesk',
    'summary': 'Project, Tasks, Repair',
    'depends': ['helpdesk_stock', 'repair'],
    'description': """
Repair Products from helpdesk tickets
    """,
    'data': [
        'views/helpdesk_views.xml',
        'views/repair_views.xml',
    ],
    'demo': ['data/helpdesk_repair_demo.xml'],
    'license': 'OEEL-1',
}
