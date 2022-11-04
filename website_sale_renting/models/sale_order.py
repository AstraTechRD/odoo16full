# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(
        self, product_id=None, line_id=None, start_date=None, end_date=None, **kwargs
    ):
        """ Override to filter on the pickup and return date for rental products. """
        lines = super()._cart_find_product_line(product_id, line_id, **kwargs)
        if not line_id and start_date and end_date:
            lines = lines.filtered(
                lambda l: l.start_date == start_date and l.return_date == end_date
            )
        return lines

    def _verify_updated_quantity(
        self, order_line, product_id, new_qty, start_date=None, end_date=None, **kwargs
    ):
        new_qty, warning = super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)
        start_date = start_date or order_line.start_date
        end_date = end_date or order_line.return_date

        if new_qty > 0 and (start_date or end_date):
            product = self.env['product.product'].browse(product_id)
            if product.rent_ok\
               and order_line._is_invalid_renting_dates(self.company_id, start_date, end_date):
                self.shop_warning = self._build_warning_renting(product, start_date, end_date)
                return 0, self.shop_warning

        return new_qty, warning

    def _prepare_order_line_values(
        self, product_id, quantity, start_date=None, end_date=None, **kwargs
    ):
        """Add corresponding pickup and return date to rental line"""
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)
        product = self.env['product.product'].browse(product_id)
        if product.rent_ok and start_date and end_date:
            values.update({
                'start_date': start_date,
                'return_date': end_date,
                'is_rental': True,
            })
            self.is_rental_order = True
        return values

    def _build_warning_renting(self, product, start_date, end_date):
        """ Build the renting warning on SO to warn user a product cannot be rented on that period.

        Note: self.ensure_one()

        :param ProductProduct product: The product concerned by the warning
        :param datetime start_date: The pickup date
        :param datetime end_date: The return date
        """
        company = self.company_id
        info = self.env['sale.order.line']._get_renting_dates_info(start_date, end_date, company)
        days_forbidden = company._get_renting_forbidden_days()
        message = _("""
            Some of your rental products (%(product)s) cannot be rented during the
            selected period and your cart must be updated. We're sorry for the
            inconvenience.
        """, product=product.name)
        if start_date < fields.Datetime.now():
            message += _("""Your rental product cannot be pickedup in the past.""")
        elif info['pickup_day'] in days_forbidden and info['return_day'] in days_forbidden:
            message += _("""
                Your rental product had invalid dates of pickup (%(start_date)s) and
                return (%(end_date)s). Unfortunately, we do not process pickups nor
                returns on those weekdays.
            """, start_date=start_date, end_date=end_date)
        elif info['pickup_day'] in days_forbidden:
            message += _("""
                Your rental product had invalid date of pickup (%(start_date)s).
                Unfortunately, we do not process pickups on that weekday.
            """, start_date=start_date)
        elif info['return_day'] in days_forbidden:
            message += _("""
                Your rental product had invalid date of return (%(end_date)s).
                Unfortunately, we do not process returns on that weekday.
            """, end_date=end_date)
        minimal_duration = company.renting_minimal_time_duration
        if info['duration'] < minimal_duration:
            message += _("""
                Your rental duration was too short. Unfortunately, we do not process
                rentals that last less than %(duration)s %(unit)s.
            """, duration=minimal_duration, unit=company.renting_minimal_time_unit)

        return message
