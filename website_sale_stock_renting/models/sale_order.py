# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_cart_and_free_qty(self, line=None, product=None, **kwargs):
        """ Override to take the rental product specificity into account

        For rental lines or product, if from and to dates are given in the kwargs the cart quantity
        becomes the maximum amount of the same product rented at the same time between from and to
        dates; The free quantity is the minimum available quantity during the same period plus the
        maximum cart quantity.

        Note: self.ensure_one()
        """
        from_date = line and line.reservation_begin or kwargs.get('start_date')
        to_date = line and line.return_date or kwargs.get('end_date')
        if (not line or not line.is_rental) \
           and (not product or not product.rent_ok) \
           or not from_date or not to_date:
            return super()._get_cart_and_free_qty(line=line, product=product, **kwargs)
        if not product:
            product = line.product_id
        common_lines = self._get_common_product_lines(line=line, product=product, **kwargs)
        qty_available = product.with_context(
            from_date=from_date, to_date=to_date, warehouse=self.warehouse_id.id
        ).qty_available
        product_rented_qties, product_key_dates = product._get_rented_quantities(
            from_date, to_date, domain=[('order_id', '!=', self.id)]
        )
        so_rented_qties, so_key_dates = common_lines._get_rented_quantities([from_date, to_date])
        current_cart_qty = max_cart_qty = 0
        current_available_qty = min_available_qty = qty_available
        key_dates = list(set(so_key_dates + product_key_dates))
        key_dates.sort()
        for i in range(1, len(key_dates)):
            start_dt = key_dates[i-1]
            if start_dt >= to_date:
                break
            current_cart_qty += so_rented_qties[start_dt]  # defaultdict
            current_available_qty -= product_rented_qties[start_dt]  # defaultdict
            max_cart_qty = max(max_cart_qty, current_cart_qty)
            min_available_qty = min(min_available_qty, current_available_qty - current_cart_qty)

        return max_cart_qty, max_cart_qty + min_available_qty

    def _get_common_product_lines(self, line=None, product=None, **kwargs):
        """ Override for rental product lines, the product should be rented during a same period.

        Filter out the lines with same product that have no common period with the current line
        renting or the from and to date given in the kwargs.

        :param SaleOrderLine line: The optional line
        :param ProductProduct product: The optional product
        :param dict kwargs: The optional arguments, where start_date and end_date are used here.
        """
        common_lines = super()._get_common_product_lines(line=line, product=product, **kwargs)
        if not common_lines\
           or ((not line or not line.is_rental) and (not product or not product.rent_ok)):
            return common_lines

        start_date = line and line.reservation_begin or kwargs.get('start_date')
        end_date = line and line.return_date or kwargs.get('end_date')
        if not start_date or not end_date:
            return common_lines

        return common_lines.filtered(
            lambda l: l.is_rental and l.reservation_begin < end_date and l.return_date > start_date
        )

    def _build_warning_renting(self, product, start_date, end_date):
        """ Override to add the message regarind preparation time
        """
        message = super()._build_warning_renting(product, start_date, end_date)
        if start_date >= fields.Datetime.now()\
           and start_date - timedelta(hours=product.preparation_time) < fields.Datetime.now():
            message += _("""Your rental product cannot be prepared on time, please rent later.""")

        return message

    def _get_cache_key_for_line(self, line):
        if not line.product_id.rent_ok:
            return super()._get_cache_key_for_line(line)
        return line.product_id, line.start_date, line.return_date

    def _get_context_for_line(self, line):
        result = super()._get_context_for_line(line)
        if line.product_id.rent_ok:
            result.update(start_date=line.start_date, end_date=line.return_date)
        return result
