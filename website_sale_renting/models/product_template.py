# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from math import ceil
from pytz import timezone, utc, UTC

from odoo import fields, models
from odoo.http import request
from odoo.addons.sale_temporal.models.product_pricing import PERIOD_RATIO
from odoo.tools import format_amount

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_combination_info(
        self, combination=False, product_id=False, add_qty=1, pricelist=False,
        parent_combination=False, only_template=False
    ):
        """Override to add the information about renting for rental products

        If the product is rent_ok, this override adds the following information about the renting :
            - is_rental: Whether combination is rental,
            - rental_duration: The duration of the first defined product pricing on this product
            - rental_unit: The unit of the first defined product pricing on this product
            - default_start_date: If no pickup nor rental date in context, the start_date of the
                                   first renting sale order line in the cart;
            - default_end_date: If no pickup nor rental date in context, the end_date of the
                                   first renting sale order line in the cart;
            - current_rental_duration: If no pickup nor rental date in context, see rental_duration,
                                       otherwise, the duration between pickup and rental date in the
                                       current_rental_unit unit.
            - current_rental_unit: If no pickup nor rental date in context, see rental_unit,
                                   otherwise the unit of the best pricing for the renting between
                                   pickup and rental date.
            - current_rental_price: If no pickup nor rental date in context, see price,
                                    otherwise the price of the best pricing for the renting between
                                    pickup and rental date.
        """
        self.ensure_one()

        combination_info = super()._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template
        )

        if self.rent_ok:
            if self.env.context.get('website_id'):
                website = self.env['website'].get_current_website()
                pricelist = pricelist or website.get_current_pricelist()
            else:
                website = False

            product = self.env['product.product'].browse(combination_info['product_id'])
            pricing = self.env['product.pricing']._get_first_suitable_pricing(
                product or self, pricelist
            )

        if not self.rent_ok or not pricing:
            # I wonder if it's useful to fill this dict with unused values.
            return {
                **combination_info,
                'is_rental': False,
            }

        # Compute best pricing rule or set default
        start_date = self.env.context.get('start_date')
        end_date = self.env.context.get('end_date')
        if pricelist and start_date and end_date:
            current_pricing = (product or self)._get_best_pricing_rule(
                start_date=start_date, end_date=end_date, pricelist=pricelist,
                currency=pricelist.currency_id
            )
            current_unit = current_pricing.recurrence_id.unit
            current_duration = self.env['product.pricing']._compute_duration_vals(
                start_date, end_date
            )[current_unit]
        else:
            current_unit = pricing.recurrence_id.unit
            current_duration = pricing.recurrence_id.duration
            current_pricing = pricing

        # Compute current price
        quantity = self.env.context.get('quantity', add_qty)
        if not pricelist:
            current_price = combination_info['price'] * (current_duration / pricing.recurrence_id.duration)
        else:
            # Here we don't add the current_attributes_price_extra nor the
            # no_variant_attributes_price_extra to the context since those prices are not added
            # in the context of rental.
            current_price = pricelist._get_product_price(
                product or self, quantity, start_date=start_date, end_date=end_date
            )

        default_start_date, default_end_date = self._get_default_renting_dates(
            start_date, end_date, only_template, website, current_duration, current_unit
        )

        ratio = ceil(current_duration) / pricing.recurrence_id.duration
        if current_unit != pricing.recurrence_id.unit:
            ratio *= PERIOD_RATIO[current_unit] / PERIOD_RATIO[pricing.recurrence_id.unit]

        company_id = False
        if website:
            #compute taxes
            product = (product or self)
            partner = self.env.user.partner_id
            company_id = website.company_id

            fpos = self.env['account.fiscal.position'].sudo()._get_fiscal_position(partner)
            product_taxes = product.sudo().taxes_id.filtered(lambda t: t.company_id == company_id)
            taxes = fpos.map_tax(product_taxes)
            current_price = self._price_with_tax_computed(
                current_price, product_taxes, taxes, company_id, pricelist, product, partner
            )

        suitable_pricings = self.env['product.pricing']._get_suitable_pricings(product or self, pricelist)
        # If there are multiple pricings with the same recurrence, we only keep the ones with the best price
        best_pricings = {}
        for p in suitable_pricings:
            if p.recurrence_id not in best_pricings:
                best_pricings[p.recurrence_id] = p
            elif best_pricings[p.recurrence_id].price > p.price:
                best_pricings[p.recurrence_id] = p
        suitable_pricings = best_pricings.values()
        currency = pricelist and pricelist.currency_id or self.env.company.currency_id
        def _pricing_price(pricing, pricelist):
            if pricing.currency_id == currency:
                return pricing.price
            return pricing.currency_id._convert(
                pricing.price,
                pricelist.currency_id,
                company_id or self.env.company,
                fields.Date.context_today(self),
            )
        pricing_table = [(p.name, format_amount(self.env, _pricing_price(p, pricelist), currency))
                            for p in suitable_pricings]

        return {
            **combination_info,
            'is_rental': True,
            'rental_duration': pricing.recurrence_id.duration,
            'rental_duration_unit': pricing.recurrence_id.unit,
            'rental_unit': pricing._get_unit_label(pricing.recurrence_id.duration),
            'default_start_date': default_start_date,
            'default_end_date': default_end_date,
            'current_rental_duration': ceil(current_duration),
            'current_rental_unit': current_pricing._get_unit_label(current_duration),
            'current_rental_price': current_price,
            'current_rental_price_per_unit': current_price / (ratio or 1),
            'base_unit_price': 0,
            'base_unit_name': False,
            'pricing_table': pricing_table,
        }

    def _get_default_renting_dates(
        self, start_date, end_date, only_template, website, duration, unit
    ):
        """ Get default renting dates to help user

        :param datetime start_date: a start_date which is directly returned if defined
        :param datetime end_date: a end_date which is directly returned if defined
        :param bool only_template: whether only the template information are needed, in this case,
                                   there will be no need to give the default renting dates.
        :param Website website: the website currently browsed by the user
        :param int duration: the duration expressed in int, in the unit given
        :param string unit: The duration unit, which can be 'hour', 'day', 'week' or 'month'
        """
        if start_date or end_date or only_template:
            return start_date, end_date

        if website and request:
            sol_rental = website.sale_get_order().order_line.filtered('is_rental')[:1]
            if sol_rental:
                end_date = max(
                    sol_rental.return_date,
                    self._get_default_end_date(sol_rental.start_date, duration, unit)
                )
                return sol_rental.start_date, end_date

        default_date = self._get_default_start_date()
        return default_date, self._get_default_end_date(default_date, duration, unit)

    def _get_default_start_date(self):
        """ Get the default pickup date and make it extensible """
        tz = timezone(self.env.user.tz or self.env.context.get('tz') or 'UTC')
        date = utc.localize(fields.Datetime.now()).astimezone(tz)
        date += relativedelta(days=1, minute=0, second=0, microsecond=0)
        return self._get_first_potential_date(date.astimezone(UTC).replace(tzinfo=None))

    def _get_default_end_date(self, start_date, duration, unit):
        """ Get the default return date based on pickup date and duration

        :param datetime start_date: the default start_date
        :param int duration: the duration expressed in int, in the unit given
        :param string unit: The duration unit, which can be 'hour', 'day', 'week' or 'month'
        """
        return self._get_first_potential_date(max(
            start_date + relativedelta(**{f'{unit}s': duration}),
            start_date + self.env.company._get_minimal_rental_duration()
        ))

    def _get_first_potential_date(self, date):
        """ Get the first potential date which respects company unavailability days settings
        """
        tz = timezone(self.env.user.tz or self.env.context.get('tz') or 'UTC')
        days_forbidden = self.env.company._get_renting_forbidden_days()
        weekday = utc.localize(date).astimezone(tz).isoweekday()
        for i in range(7):
            if ((weekday + i) % 7 or 7) not in days_forbidden:
                break
        return date + relativedelta(days=i)

    def _search_render_results_prices(self, mapping, combination_info):
        if not combination_info['is_rental']:
            return super()._search_render_results_prices(mapping, combination_info)

        return self.env['ir.ui.view']._render_template(
            'website_sale_renting.rental_search_result_price',
            values={
                'currency': mapping['detail']['display_currency'],
                'price': combination_info['price'],
                'duration': combination_info['rental_duration'],
                'unit': combination_info['rental_unit'],
            }
        ), None

    def _get_sales_prices(self, pricelist):
        prices = super()._get_sales_prices(pricelist)

        for template in self:
            if not template.rent_ok:
                continue
            pricing = self.env['product.pricing']._get_first_suitable_pricing(template, pricelist)
            if pricing:
                prices[template.id]['rental_duration'] = pricing.recurrence_id.duration
                prices[template.id]['rental_unit'] = pricing._get_unit_label(pricing.recurrence_id.duration)
            else:
                prices[template.id]['rental_duration'] = 0
                prices[template.id]['rental_unit'] = False

        return prices

    def _website_show_quick_add(self):
        self.ensure_one()
        return not self.rent_ok and super()._website_show_quick_add()

    def _search_get_detail(self, website, order, options):
        search_details = super()._search_get_detail(website, order, options)
        if options.get('rent_only') or (options.get('from_date') and options.get('to_date')):
            search_details['base_domain'].append([('rent_ok', '=', True)])
        return search_details
