# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import _, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _set_shop_warning_stock(self, desired_qty, new_qty):
        """ Override shop_warning to adapt message for rent ok products.
        """
        self.ensure_one()
        if not self.is_rental:
            return super()._set_shop_warning_stock(desired_qty, new_qty)
        # tell user that the desired qty means the MAX number of products rented at the same time
        # during the period
        self.shop_warning = _(
            """
            You asked for %(desired_qty)s products but only %(new_qty)s are available from
            %(rental_period)s.
            """,
            desired_qty=desired_qty, new_qty=new_qty,
            rental_period=self._get_rental_order_line_description()
        )

    def _get_rented_quantities(self, mandatory_dates):
        """ Get rented quantities dict and ordered dict keys for the given period

        The values of the dict represents the amount of product that are picked-up at `key`
        datetime. The key dates are returned sorted to be used in other algorithms.

        :param list(datetime) mandatory_dates: dates that should be added to the dict
        """
        if len(self.product_id) > 1:
            raise ValueError("Expected singleton or no record: %s" % self.product_id)
        rented_quantities = defaultdict(float)
        for so_line in self:
            qty_to_deliver = so_line.product_uom_qty - so_line.qty_delivered
            qty_to_return = so_line.product_uom_qty - so_line.qty_returned
            rented_quantities[so_line.reservation_begin] += qty_to_deliver
            rented_quantities[so_line.return_date] -= qty_to_return

        # Key dates means either the dates of the keys, either the fact that those dates are key
        # dates, where there is a quantity modification.
        key_dates = list(set(rented_quantities.keys()) | set(mandatory_dates))
        key_dates.sort()
        return rented_quantities, key_dates

    def _get_max_available_qty(self):
        if self.is_rental:
            cart_qty, free_qty = self.order_id._get_cart_and_free_qty(line=self)
            return free_qty - cart_qty
        return super()._get_max_available_qty()

    def _is_invalid_renting_dates(self, company, start_date=None, end_date=None):
        """ Check the pickup and return dates are invalid
        """
        preparation_delta = timedelta(hours=self.product_id.preparation_time)
        return super()._is_invalid_renting_dates(company, start_date=start_date, end_date=end_date)\
            or ((self.start_date or start_date) - preparation_delta) < fields.Datetime.now()
