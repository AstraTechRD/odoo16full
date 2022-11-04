# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.osv import expression

from odoo.addons.website.models import ir_http

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_cart_qty(self, website=None):
        """ Override of the website_sale_stock to take into account rental products.
        """
        start_date = self.env.context.get('start_date')
        end_date = self.env.context.get('end_date')
        if not self.allow_out_of_stock_order and start_date and end_date:
            website = website or self.env['website'].get_current_website()
            cart = website and request and website.sale_get_order() or None
            if cart:
                return sum(
                    cart._get_common_product_lines(
                        product=self, start_date=start_date, end_date=end_date
                    ).mapped('product_uom_qty')
                )
        return super()._get_cart_qty(website)

    def _get_rented_quantities(self, from_date, to_date, domain=None):
        """ Get the rented quantities for all the rental sale order line with product self.

        Note: self.ensure_one()

        :param datetime from_date: The first date where a rental sale order line is returned.
        :param datetime to_date: The last date where a rental sale order line reservation begins.
        :param list(tuple) domain: An additional restrictive domain to search sale order line for.

        :return:
        :rtype:
        """
        self.ensure_one()

        return self.env['sale.order.line'].search(
            expression.AND([
                domain or [],
                [
                    ('is_rental', '=', True),
                    ('product_id', '=', self.id),
                    ('state', 'in', ['sent', 'sale', 'done']),  # FIXME TLE: sent ?
                    ('return_date', '>', from_date),
                    ('reservation_begin', '<', to_date),
                ],
            ]),
            order="reservation_begin asc"
        )._get_rented_quantities([from_date, to_date])

    def _get_availabilities(self, from_date, to_date, warehouse_id, with_cart=False):
        """ Return a list of availabilities for a given period.

        The availabilities are structured in a dictionary of keys :
            - start: The date where the available_quantity becomes valid.
            - end: The date where the available_quantity becomes invalid.
            - available_quantity: The quantity of products available between the two dates.

        Doesn't count already returned quantities.

        Note: self.ensure_one()

        :param datetime from_date: The date from which the availabilities should be computed
        :param datetime to_date: The date to which the availabilities should be computed
        :param int warehouse_id: The warehouse id
        """
        self.ensure_one()

        # This implementation is not perfect since qty_available is a poor float field which is,
        # in fact, equal to min(qty_available(t)) for t in [from_date, to_date]
        qty_available = self.with_context(
            from_date=from_date,
            to_date=to_date,
            warehouse=warehouse_id
        ).qty_available
        rented_quantities, key_dates = self._get_rented_quantities(from_date, to_date, domain=[
            ('order_id.warehouse_id', '=', warehouse_id)
        ])
        website = with_cart and ir_http.get_request_website()
        cart = website and website.sale_get_order()
        if cart:
            common_lines = cart._get_common_product_lines(
                product=self, start_date=from_date, end_date=to_date
            )
            so_rented_qties, so_key_dates = common_lines._get_rented_quantities([from_date, to_date])
            key_dates = list(set(so_key_dates + key_dates))
            key_dates.sort()
        current_qty_available = qty_available
        availabilities = []
        for i in range(1, len(key_dates)):
            start_dt = key_dates[i-1]
            if start_dt > to_date:
                break
            # We consider here the worst case scenario, where qty_available is constant for the
            # whole period
            current_qty_available -= rented_quantities[start_dt]
            if cart:
                current_qty_available -= so_rented_qties[start_dt]
            if start_dt >= from_date:
                availabilities.append({
                    'start': start_dt,
                    'end': key_dates[i],
                    'quantity_available': current_qty_available,
                })

        return availabilities
