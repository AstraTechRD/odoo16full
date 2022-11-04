# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import main

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError


class PaymentPortal(main.PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, *args, **kwargs):
        """ Payment transaction override to double check cart renting periods before
        placing the order
        """
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.is_rental and line._is_invalid_renting_dates(order.company_id):
                values.append(order._build_warning_renting(
                    line.product_id, line.start_date, line.return_date
                ))
        if values:
            raise ValidationError(' '.join(values))
        return super().shop_payment_transaction(*args, **kwargs)
