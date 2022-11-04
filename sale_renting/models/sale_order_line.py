# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, date
from pytz import timezone, UTC

from odoo import api, fields, models, _
from odoo.tools import format_datetime, format_time


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_rental = fields.Boolean(default=False)

    qty_returned = fields.Float("Returned", default=0.0, copy=False)
    start_date = fields.Datetime(string='Start Date')
    return_date = fields.Datetime(string="Return")
    reservation_begin = fields.Datetime(
        string="Pickup date - padding time", compute='_compute_reservation_begin', store=True)

    is_late = fields.Boolean(
        string="Is overdue", compute='_compute_is_late',
        help="The products haven't been returned in time")

    is_product_rentable = fields.Boolean(related='product_id.rent_ok', depends=['product_id'])
    temporal_type = fields.Selection(selection_add=[('rental', 'Rental')])

    @api.depends('product_template_id', 'is_rental')
    def _compute_temporal_type(self):
        super()._compute_temporal_type()
        for line in self:
            # We only rely on the is_rental stored boolean because after migration, product could be migrated
            # with rent_ok = False It will ensure that rental line are still considered rental even if the product change
            # To compare with subscription where temporal type depends on recurrency and recurring_invoice
            if line.is_rental:
                line.temporal_type = 'rental'

    @api.depends('return_date')
    def _compute_is_late(self):
        now = fields.Datetime.now()
        for line in self:
            # By default, an order line is considered late only if it has one hour of delay
            line.is_late = line.return_date and line.return_date + timedelta(hours=self.company_id.min_extra_hour) < now

    @api.depends('start_date')
    def _compute_reservation_begin(self):
        lines = self.filtered(lambda line: line.is_rental)
        for line in lines:
            line.reservation_begin = line.start_date
        (self - lines).reservation_begin = None

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clean rental related data if new product cannot be rented."""
        if (not self.is_product_rentable) and self.is_rental:
            self.update({
                'is_rental': False,
                'start_date': False,
                'return_date': False,
            })

    @api.onchange('qty_delivered')
    def _onchange_qty_delivered(self):
        """When picking up more than reserved, reserved qty is updated"""
        if self.qty_delivered > self.product_uom_qty:
            self.product_uom_qty = self.qty_delivered

    @api.depends('start_date', 'return_date', 'is_rental')
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()

    @api.onchange('is_rental')
    def _onchange_is_rental(self):
        if self.is_rental and not self.order_id.is_rental_order:
            self.order_id.is_rental_order = True

    _sql_constraints = [
        ('rental_stock_coherence',
            "CHECK(NOT is_rental OR qty_returned <= qty_delivered)",
            "You cannot return more than what has been picked up."),
        ('rental_period_coherence',
            "CHECK(NOT is_rental OR start_date < return_date)",
            "Please choose a return date that is after the pickup date."),
    ]

    def _get_sale_order_line_multiline_description_sale(self):
        """Add Rental information to the SaleOrderLine name."""
        res = super()._get_sale_order_line_multiline_description_sale()
        if self.is_rental:
            res += self._get_rental_order_line_description()
        return res

    def _get_rental_order_line_description(self):
        tz = self._get_tz()
        if self.start_date and self.return_date\
           and self.start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()\
               == self.return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date():
            # If return day is the same as pickup day, don't display return_date Y/M/D in description.
            return_date_part = format_time(self.with_context(use_babel=True).env, self.return_date, tz=tz, time_format=False)
        else:
            return_date_part = format_datetime(self.with_context(use_babel=True).env, self.return_date, tz=tz, dt_format=False)

        return "\n%s %s %s" % (
            format_datetime(self.with_context(use_babel=True).env, self.start_date, tz=tz, dt_format=False),
            _("to"),
            return_date_part,
        )

    def _generate_delay_line(self, qty):
        """Generate a sale order line representing the delay cost due to the late return.

        :param float qty:
        :param timedelta duration:
        """
        self.ensure_one()
        if qty <= 0 or not self.is_late:
            return

        duration = fields.Datetime.now() - self.return_date

        delay_price = self.product_id._compute_delay_price(duration)
        if delay_price <= 0.0:
            return

        # migrate to a function on res_company get_extra_product?
        delay_product = self.company_id.extra_product
        if not delay_product:
            delay_product = self.env['product.product'].with_context(active_test=False).search(
                [('default_code', '=', 'RENTAL'), ('type', '=', 'service')], limit=1)
            if not delay_product:
                delay_product = self.env['product.product'].create({
                    "name": "Rental Delay Cost",
                    "standard_price": 0.0,
                    "type": 'service',
                    "default_code": "RENTAL",
                    "purchase_ok": False,
                })
                # Not set to inactive to allow users to put it back in the settings
                # In case they removed it.
            self.company_id.extra_product = delay_product

        if not delay_product.active:
            return

        delay_price = self.product_id.currency_id._convert(
            from_amount=delay_price,
            to_currency=self.currency_id,
            company=self.company_id,
            date=date.today(),
        )

        vals = self._prepare_delay_line_vals(delay_product, delay_price, qty)

        self.order_id.write({
            'order_line': [(0, 0, vals)]
        })

    def _prepare_delay_line_vals(self, delay_product, delay_price, qty):
        """Prepare values of delay line.

        :param float delay_price:
        :param float quantity:
        :param delay_product: Product used for the delay_line
        :type delay_product: product.product
        :return: sale.order.line creation values
        :rtype dict:
        """
        delay_line_description = self._get_delay_line_description()
        return {
            'name': delay_line_description,
            'product_id': delay_product.id,
            'product_uom_qty': qty,
            'product_uom': self.product_id.uom_id.id,
            'qty_delivered': qty,
            'price_unit': delay_price,
        }

    def _get_delay_line_description(self):
        # Shouldn't tz be taken from self.order_id.user_id.tz ?
        tz = self._get_tz()
        return "%s\n%s: %s\n%s: %s" % (
            self.product_id.name,
            _("Expected"),
            format_datetime(self.with_context(use_babel=True).env, self.return_date, tz=tz, dt_format=False),
            _("Returned"),
            format_datetime(self.with_context(use_babel=True).env, fields.Datetime.now(), tz=tz, dt_format=False)
        )

    #=== ONCHANGE METHODS ===#

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clean product related data if new product is not temporal."""
        if not self.temporal_type:
            values = self._get_clean_up_values()
            self.update(values)

    def _get_clean_up_values(self):
        """Helper to allow reset lines values."""
        return {'return_date': False}

    def _get_tz(self):
        return self.env.context.get('tz') or self.env.user.tz or 'UTC'

    # === PRICE COMPUTING HOOKS === #

    def _get_price_computing_kwargs(self):
        """ Override to add the pricing duration or the start and end date of temporal line """
        price_computing_kwargs = super()._get_price_computing_kwargs()
        if self.temporal_type != 'rental':
            return price_computing_kwargs
        if self.start_date and self.return_date:
            price_computing_kwargs['start_date'] = self.start_date
            price_computing_kwargs['end_date'] = self.return_date
        return price_computing_kwargs
