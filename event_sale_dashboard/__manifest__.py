# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Events Sales Dashboard",
    'version': '1.0',
    'website': 'https://www.odoo.com/app/events',
    'summary': "Add dashboard for Event Revenues Report",
    'description': """This module helps for analyzing revenues from events.
For that purpose it adds a dashboard view to the revenues report
    """,
    'category': 'Marketing/Events',
    'depends': ['event_sale'],
    'data': [
        'report/event_sale_report_views.xml',
    ],
    'auto_install': ['event_sale'],
    'application': False,
    'license': 'OEEL-1',
}
