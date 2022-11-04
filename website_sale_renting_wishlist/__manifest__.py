{
    'name': 'eCommerce Rental with Wishlist',
    'category': 'Hidden',
    'summary': 'Sell rental products on your eCommerce from Wishlist',
    'version': '1.0',
    'description': """
This module allows you to sell rental products in your eCommerce Wishlist.
    """,
    'depends': ['website_sale_renting', 'website_sale_wishlist'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_renting_wishlist/static/src/js/**.js',
        ],
        'web.assets_tests': [
            'website_sale_renting_wishlist/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
