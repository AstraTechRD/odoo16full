# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Peruvian - Electronic Delivery Note""",
    'version': '0.1.',
    'summary': 'Electronic Delivery Note for Peru (OSE method) and UBL 2.1',
    'category': 'Accounting/Localizations/EDI',
    'author': 'Vauxoo',
    'license': 'OEEL-1',
    'description': """
    The delivery guide (Guía de Remisión) is needed as a proof
    that you are sending goods between A and B.

    It is only when a delivery order is validated that you can create the delivery
    guide.
    """,
    'depends': [
        'delivery',
        'l10n_pe_edi',
    ],
    "demo": [
        'demo/res_partner.xml',
        'demo/vehicle.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/delivery_security.xml',
        'views/stock_picking_views.xml',
        'data/edi_delivery_guide.xml',
        'views/report_deliveryslip.xml',
        'views/vehicle_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
