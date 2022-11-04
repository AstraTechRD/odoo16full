# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import format_amount
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_pricing_ids = fields.One2many('product.pricing', 'product_template_id', string="Custom Pricings", auto_join=True, copy=True)
    is_temporal = fields.Boolean(compute='_compute_is_temporal')
    display_price = fields.Char("Leasing price", help="First leasing pricing of the product", compute="_compute_display_price")

    @api.model
    def _get_incompatible_types(self):
        return []

    def _check_incompatible_types(self):
        incomptatible_types = self._get_incompatible_types()
        if len(incomptatible_types) < 2:
            return
        fields = self.env['ir.model.fields'].search_read(
            [('model', '=', 'product.template'), ('name', 'in', incomptatible_types)],
            ['field_description'])
        field_descriptions = [v['field_description'] for v in fields]
        field_list = incomptatible_types + ['name']
        values = self.read(field_list)
        for val in values:
            incompatible_values = [val[f] for f in self._get_incompatible_types() if val[f]]
            if len(incompatible_values) > 1:
                raise ValidationError(_("The product (%s) has incompatible values: %s",
                                        val['name'], ','.join(field_descriptions)))

    def _compute_is_temporal(self):
        self.is_temporal = False

    def _compute_display_price(self):
        temporal_products = self.filtered('is_temporal')
        temporal_priced_products = temporal_products.filtered('product_pricing_ids')
        (self - temporal_products).display_price = ""
        for product in (temporal_products - temporal_priced_products):
            product.display_price = _("%(amount)s (fixed)", amount=format_amount(self.env, product.list_price, product.currency_id))
        # No temporal pricing defined, fallback on list price
        for product in temporal_priced_products:
            product.display_price = product.product_pricing_ids[0].description

    def _get_best_pricing_rule(
        self, product=False, start_date=False, end_date=False, duration=False, unit='', **kwargs
    ):
        """ Return the best pricing rule for the given duration.

        :param ProductProduct product: a product recordset (containing at most one record)
        :param float duration: duration, in unit uom
        :param str unit: duration unit (hour, day, week)
        :param datetime start_date: start date of leasing period
        :param datetime end_date: end date of leasing period
        :return: least expensive pricing rule for given duration
        """
        self.ensure_one()
        best_pricing_rule = self.env['product.pricing']
        if not self.product_pricing_ids:
            return best_pricing_rule
        # Two possibilities: start_date and end_date are provided or the duration with its unit.
        pricelist = kwargs.get('pricelist', self.env['product.pricelist'])
        currency = kwargs.get('currency', self.currency_id)
        company = kwargs.get('company', self.env.company)
        duration_dict = {}
        if start_date and end_date:
            duration_dict = self.env['product.pricing']._compute_duration_vals(start_date, end_date)
        elif not (duration and unit):
            return best_pricing_rule  # no valid input to compute duration.
        min_price = float("inf")  # positive infinity
        Pricing = self.env['product.pricing']
        available_pricings = Pricing._get_suitable_pricings(product or self, pricelist=pricelist)
        for pricing in available_pricings:
            if duration and unit:
                price = pricing._compute_price(duration, unit)
            else:
                price = pricing._compute_price(duration_dict[pricing.recurrence_id.unit], pricing.recurrence_id.unit)
            if pricing.currency_id != currency:
                price = pricing.currency_id._convert(
                    from_amount=price,
                    to_currency=currency,
                    company=company,
                    date=fields.Date.today(),
                )
            # We compare the abs of prices because negative pricing (as a promotion) would trigger the
            # highest discount without it.
            if abs(price) < abs(min_price):
                min_price, best_pricing_rule = price, pricing
        return best_pricing_rule
