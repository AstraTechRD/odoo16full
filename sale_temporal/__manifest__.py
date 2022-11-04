# -*- coding: utf-8 -*-
{
    'name': "Sale Lease",
    'summary': """
        Extend sale flow to sell/lease/rent a product depending on duration, quantity, price list""",

    'description': """This technical module allows to define lease prices on a product template and use them in sale order according to a duration, a quantity, a price list.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'installable': True,
    'license': 'OEEL-1',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_pricing_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_template_views.xml',
        'views/sale_temporal_recurrence_views.xml',
        'views/sale_order_views.xml',
        'data/sale_temporal_data.xml',
    ],
}
