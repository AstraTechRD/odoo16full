# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Settle Due',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': "Settle partner's due in the POS UI.",
    'depends': ['point_of_sale', 'account_followup'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale.assets': [
            'pos_settle_due/static/src/css/pos.css',
            'pos_settle_due/static/src/js/**/*.js',
            'pos_settle_due/static/src/xml/**/*.xml',
        ],
    }
}
