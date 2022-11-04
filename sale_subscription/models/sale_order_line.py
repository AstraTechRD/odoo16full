# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import fields, models, api, _, Command
from odoo.tools.date_utils import get_timedelta
from odoo.tools import format_date
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import ValidationError

INTERVAL_FACTOR = {
    'day': 30.437,  # average number of days per month over the year,
    'week': 30.437 / 7.0,
    'month': 1.0,
    'year': 1.0 / 12.0,
}


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    temporal_type = fields.Selection(selection_add=[('subscription', 'Subscription')])
    pricing_id = fields.Many2one('product.pricing',
                                 compute='_compute_pricing', store=True, precompute=True)
    recurring_monthly = fields.Monetary(compute='_compute_recurring_monthly', string="Monthly Recurring Revenue")
    parent_line_id = fields.Many2one('sale.order.line', compute='_compute_parent_line_id', store=True, precompute=True)

    def _check_line_unlink(self):
        """ Override. Check wether a line can be deleted or not."""
        undeletable_lines = super()._check_line_unlink()
        not_subscription_lines = self.filtered(lambda line: not line.order_id.is_subscription)
        return not_subscription_lines and undeletable_lines

    @api.depends('product_template_id', 'order_id.recurrence_id')
    def _compute_temporal_type(self):
        super()._compute_temporal_type()
        for line in self:
            if line.product_template_id.recurring_invoice and line.order_id.recurrence_id:
                line.temporal_type = 'subscription'

    @api.depends('order_id.is_subscription', 'temporal_type')
    def _compute_invoice_status(self):
        skip_line_status_compute = self.env.context.get('skip_line_status_compute')
        if skip_line_status_compute:
            return
        super(SaleOrderLine, self)._compute_invoice_status()
        today = fields.Date.today()
        for line in self:
            if not line.order_id.is_subscription or line.temporal_type != 'subscription':
                continue
            # Subscriptions and upsells
            to_invoice_check = line.order_id.next_invoice_date and line.state in ('sale', 'done') and line.order_id.next_invoice_date >= today
            if line.order_id.end_date:
                to_invoice_check = to_invoice_check and line.order_id.end_date > today
            if to_invoice_check and line.order_id.start_date and line.order_id.start_date > today or float_is_zero(line.price_subtotal, precision_rounding=line.order_id.currency_id.rounding):
                line.invoice_status = 'no'

    @api.depends('order_id.subscription_management', 'order_id.start_date', 'order_id.next_invoice_date')
    def _compute_discount(self):
        today = fields.Date.today()
        other_lines = self.env['sale.order.line']
        for line in self:
            if not line.order_id.next_invoice_date or line.order_id.subscription_management != 'upsell':
                other_lines |= line
                continue
            period_end = line.order_id.next_invoice_date
            current_period_start = line.order_id.start_date or today
            previous_period_start = line.order_id.subscription_id.last_invoice_date or line.order_id.subscription_id.start_date
            time_to_invoice = period_end - current_period_start
            if period_end and (period_end - previous_period_start).days != 0:
                ratio = float(time_to_invoice.days) / float((period_end - previous_period_start).days)
            else:
                ratio = 1
            # Warning: we allow here ratio > 1 to be able to have negative discount.
            # Negative discount are useful when we want to upsell a renewal order that not started yet.
            # In that case, the upsell will also impact the renewed contract for a prorata temporis of the previous period
            if ratio < 0:
                ratio = 1.00  # Something went wrong in the dates
            if line.order_id.subscription_management == 'upsell' and line.product_id.recurring_invoice and line.order_id.next_invoice_date:
                line.discount = (1 - ratio) * 100
                if line.parent_line_id:
                    # If the parent line had a discount, we reapply it to keep the same conditions. E.G. base price is 200€
                    # parent line has a 10% discount and upsell has a 25% discount.
                    # We want to apply a final price equal to 200 * 0.75 (prorata) * 0.9 (discount) = 135 or 200*0,675
                    # We save 32.5 in the discount
                    line.discount = (1 - (1 - line.discount / 100) * (1 - line.parent_line_id.discount / 100)) * 100
        return super(SaleOrderLine, other_lines)._compute_discount()

    @api.depends('order_id.recurrence_id', 'parent_line_id')
    def _compute_price_unit(self):
        line_to_recompute = self.env['sale.order.line']
        for line in self:
            if not line.parent_line_id:
                line_to_recompute |= line
                continue
            line.price_unit = line.parent_line_id.price_unit
        super(SaleOrderLine, line_to_recompute)._compute_price_unit()

    @api.depends('product_id', 'order_id.recurrence_id')
    def _compute_pricing(self):
        # search pricing_ids for each variant in self
        available_pricing_ids = self.env['product.pricing'].search([
            ('product_template_id', 'in', self.product_id.product_tmpl_id.ids),
            ('recurrence_id', 'in', self.order_id.recurrence_id.ids),
            '|',
            ('product_variant_ids', 'in', self.product_id.ids),
            ('product_variant_ids', '=', False),
            '|',
            ('pricelist_id', 'in', self.order_id.pricelist_id.ids),
            ('pricelist_id', '=', False)
        ])
        for line in self:
            if not line.product_id.recurring_invoice:
                line.pricing_id = False
                continue
            line.pricing_id = available_pricing_ids.filtered(
                lambda pricing:
                    line.product_id.product_tmpl_id == pricing.product_template_id and (
                        line.product_id in pricing.product_variant_ids or not pricing.product_variant_ids
                    ) and (line.order_id.pricelist_id == pricing.pricelist_id or not pricing.pricelist_id)
            )[:1]

    @api.depends('temporal_type', 'invoice_lines.subscription_start_date', 'invoice_lines.subscription_end_date',
                 'order_id.next_invoice_date', 'order_id.last_invoice_date')
    def _compute_qty_to_invoice(self):
        return super()._compute_qty_to_invoice()

    def _get_invoice_lines(self):
        self.ensure_one()
        if self.temporal_type != 'subscription':
            return super()._get_invoice_lines()
        else:
            last_invoice_date = self.order_id.last_invoice_date or self.order_id.start_date
            invoice_line = self.invoice_lines.filtered(
                lambda line: line.date and last_invoice_date and line.date > last_invoice_date)
            return invoice_line

    def _get_subscription_qty_to_invoice(self, last_invoice_date=False, next_invoice_date=False):
        result = {}
        qty_invoiced = self._get_subscription_qty_invoiced(last_invoice_date, next_invoice_date)
        for line in self:
            if line.state not in ['sale', 'done']:
                continue
            if line.product_id.invoice_policy == 'order':
                result[line.id] = line.product_uom_qty - qty_invoiced.get(line.id, 0.0)
            else:
                result[line.id] = line.qty_delivered - qty_invoiced.get(line.id, 0.0)
        return result

    def _get_subscription_qty_invoiced(self, last_invoice_date=None, next_invoice_date=None):
        result = {}
        amount_sign = {'out_invoice': 1, 'out_refund': -1}
        for line in self:
            if line.temporal_type != 'subscription' or line.order_id.state not in ['sale', 'done']:
                continue
            qty_invoiced = 0.0
            last_period_start = line.order_id.next_invoice_date and line.order_id.next_invoice_date - get_timedelta(line.order_id.recurrence_id.duration, line.order_id.recurrence_id.unit)
            start_date = last_invoice_date or last_period_start
            end_date = next_invoice_date or line.order_id.next_invoice_date
            day_before_end_date = end_date and end_date - relativedelta(days=1)
            if not start_date or not day_before_end_date:
                continue
            # The related_invoice_lines have their subscription_{start,end}_date between start_date and day_before_end_date
            # But sometimes, migrated contract and account_move_line don't have these value set.
            # We fall back on the  l.move_id.invoice_date which could be wrong if the invoice is posted during another
            # period than the subscription.
            related_invoice_lines = line.invoice_lines.filtered(
                lambda l: l.move_id.state != 'cancel' and
                        l.subscription_start_date and l.subscription_end_date and
                        start_date <= l.subscription_start_date <= day_before_end_date and
                        l.subscription_end_date == day_before_end_date)
            for invoice_line in related_invoice_lines:
                line_sign = amount_sign.get(invoice_line.move_id.move_type, 1)
                qty_invoiced += line_sign * invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
            result[line.id] = qty_invoiced
        return result

    @api.depends('temporal_type', 'invoice_lines', 'invoice_lines.subscription_start_date',
                 'invoice_lines.subscription_end_date', 'order_id.next_invoice_date', 'order_id.last_invoice_date')
    def _compute_qty_invoiced(self):
        other_lines = self.env['sale.order.line']
        subscription_qty_invoiced = self._get_subscription_qty_invoiced()
        for line in self:
            if line.temporal_type != 'subscription':
                other_lines |= line
                continue
            line.qty_invoiced = subscription_qty_invoiced.get(line.id, 0.0)
        super(SaleOrderLine, other_lines)._compute_qty_invoiced()

    @api.depends('temporal_type', 'price_subtotal', 'pricing_id')
    def _compute_recurring_monthly(self):
        subscription_lines = self.filtered(lambda l: l.temporal_type == 'subscription')
        for line in subscription_lines:
            if not line.order_id.recurrence_id:
                continue
            if line.order_id.recurrence_id.unit not in INTERVAL_FACTOR.keys():
                raise ValidationError(_("The time unit cannot be used. Please chose one of these unit: %s.",
                                        ", ".join(['Month, Year', 'One Time'])))
            line.recurring_monthly = line.price_subtotal * INTERVAL_FACTOR[line.order_id.recurrence_id.unit] / line.order_id.recurrence_id.duration
        (self - subscription_lines).recurring_monthly = 0

    @api.depends('order_id.subscription_id', 'product_id', 'product_uom', 'price_unit', 'order_id')
    def _compute_parent_line_id(self):
        parent_line_ids = self.order_id.subscription_id.order_line
        for line in self:
            if not line.order_id.subscription_id or not line.product_id.recurring_invoice:
                continue
            # We use a rounding to avoid -326.40000000000003 != -326.4 for new records.
            matching_line_ids = parent_line_ids.filtered(
                lambda l:
                (l.order_id, l.product_id, l.product_uom, l.order_id.currency_id,
                 l.order_id.currency_id.round(l.price_unit) if l.order_id.currency_id else round(l.price_unit, 2)) ==
                (line.order_id.subscription_id, line.product_id, line.product_uom, line.order_id.currency_id,
                 line.order_id.currency_id.round(line.price_unit) if line.order_id.currency_id else round(line.price_unit, 2)
                 )
            )
            if matching_line_ids:
                line.parent_line_id = matching_line_ids.ids[-1]
            else:
                line.parent_line_id = False

    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        res = super()._prepare_invoice_line(**optional_values)
        if not self.display_type and (self.temporal_type == 'subscription' or self.order_id.subscription_management == 'upsell'):
            product_desc = self.product_id.get_product_multiline_description_sale() + self._get_sale_order_line_multiline_description_variants()
            description = _("%(product)s - %(duration)d %(unit)s",
                            product=product_desc,
                            duration=round(self.order_id.recurrence_id.duration),
                            unit=self.order_id.recurrence_id.unit)
            lang_code = self.order_id.partner_id.lang
            if self.qty_invoiced:
                # We need to invoice the next period: last_invoice_date will be today once this invoice is created. We use get_timedelta to avoid gaps
                new_period_start = self.order_id.next_invoice_date
            else:
                # First invoice for a given period. This period may start today
                new_period_start = self.order_id.start_date or fields.Datetime.today()
            format_start = format_date(self.env, new_period_start, lang_code=lang_code)
            parent_order_id = self.order_id.id
            if self.order_id.subscription_management == 'upsell':
                # remove 1 day as normal people thinks in terms of inclusive ranges.
                next_invoice_date = self.order_id.next_invoice_date - relativedelta(days=1)
                parent_order_id = self.order_id.subscription_id.id
            else:
                default_next_invoice_date = new_period_start + get_timedelta(self.order_id.recurrence_id.duration,
                                                                             self.order_id.recurrence_id.unit)
                # remove 1 day as normal people thinks in terms of inclusive ranges.
                next_invoice_date = default_next_invoice_date - relativedelta(days=1)

            format_invoice = format_date(self.env, next_invoice_date, lang_code=lang_code)
            description += _("\n%s to %s", format_start, format_invoice)

            qty_to_invoice = self._get_subscription_qty_to_invoice(last_invoice_date=new_period_start,
                                                                   next_invoice_date=next_invoice_date)
            subscription_end_date = next_invoice_date
            res['quantity'] = qty_to_invoice.get(self.id, 0.0)

            res.update({
                'name': description,
                'subscription_start_date': new_period_start,
                'subscription_end_date': subscription_end_date,
                'subscription_id': parent_order_id,
            })
        return res

    def _reset_subscription_qty_to_invoice(self):
        """ Define the qty to invoice on subscription lines equal to product_uom_qty for recurring lines
            It allows avoiding using the _compute_qty_to_invoice with a context_today
        """
        today = fields.Date.today()
        for line in self:
            if not line.temporal_type == 'subscription' or line.product_id.invoice_policy == 'delivery' or line.order_id.start_date and line.order_id.start_date > today:
                continue
            line.qty_to_invoice = line.product_uom_qty

    def _reset_subscription_quantity_post_invoice(self):
        """ Update the Delivered quantity value of recurring line according to the periods
        """
        # arj todo: reset only timesheet things. So reset nothing in standard but override in sale-subscription_timesheet (to be recreated...)
        return

    ####################
    # Business Methods #
    ####################

    def _get_renew_upsell_values(self, subscription_management, period_end=None):
        order_lines = []
        description_needed = False
        for line in self:
            if line.temporal_type != 'subscription':
                continue
            partner_lang = line.order_id.partner_id.lang
            line = line.with_context(lang=partner_lang) if partner_lang else line
            product = line.product_id
            order_lines.append((0, 0, {
                'parent_line_id': line.id,
                'temporal_type': 'subscription',
                'product_id': product.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': 0 if subscription_management == 'upsell' else line.product_uom_qty,
                'price_unit': line.price_unit,
            }))
            description_needed = True
        if subscription_management == 'upsell' and description_needed and period_end:
            format_start = format_date(self.env, fields.Date.today())
            end_period = period_end - relativedelta(days=1)  # the period ends the day before the next invoice
            format_next_invoice = format_date(self.env, end_period)
            order_lines.append((
                0,
                0,
                {
                    'display_type': 'line_note',
                    'sequence': 999,
                    'name': _('Recurring product are discounted according to the prorated period from %s to %s', format_start, format_next_invoice)
                }
            ))

        return order_lines

    def _subscription_update_line_data(self, subscription):
        """
        Prepare a dictionary of values to add or update lines on a subscription.
        :return: order_line values to create or update the subscription
        """
        update_values = []
        create_values = []
        dict_changes = {}
        for line in self:
            sub_line = line.parent_line_id
            if sub_line:
                # We have already a subscription line, we need to modify the product quantity
                if len(sub_line) > 1:
                    # we are in an ambiguous case
                    # to avoid adding information to a random line, in that case we create a new line
                    # we can simply duplicate an arbitrary line to that effect
                    sub_line[0].copy({'name': line.display_name, 'product_uom_qty': line.product_uom_qty})
                elif line.product_uom_qty != 0:
                    dict_changes.setdefault(sub_line.id, sub_line.product_uom_qty)
                    # upsell, we add the product to the existing quantity
                    dict_changes[sub_line.id] += line.product_uom_qty
            else:
                # we create a new line in the subscription:
                create_values.append(Command.create({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'discount': 0,
                    'pricing_id': line.pricing_id.id,
                    'order_id': subscription.id
                }))
        update_values += [(1, sub_id, {'product_uom_qty': dict_changes[sub_id]}) for sub_id in dict_changes]
        return create_values, update_values

    # === PRICE COMPUTING HOOKS === #

    def _get_price_computing_kwargs(self):
        """ Override to add the pricing duration or the start and end date of temporal line """
        price_computing_kwargs = super()._get_price_computing_kwargs()
        if self.temporal_type != 'subscription':
            return price_computing_kwargs
        if self.order_id.recurrence_id:
            price_computing_kwargs['duration'] = self.order_id.recurrence_id.duration
            price_computing_kwargs['unit'] = self.order_id.recurrence_id.unit
        return price_computing_kwargs
