{
    'name': 'eCommerce Rental with Comparison',
    'category': 'Hidden',
    'summary': 'Sell rental products on your eCommerce from Comparison page',
    'version': '1.0',
    'description': """
This module allows you to sell rental products in your eCommerce Comparison page.
    """,
    'depends': ['website_sale_renting', 'website_sale_comparison'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_renting_comparison/static/src/js/**.js',
        ],
        'web.assets_tests': [
            'website_sale_renting_comparison/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
