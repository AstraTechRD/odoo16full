# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request

class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.constrains('optional_product_ids')
    def _constraints_optional_product_ids(self):
        for template in self:
            for optional_template in template.optional_product_ids:
                if self.env['product.pricing']._get_first_suitable_pricing(template).recurrence_id != \
                        self.env['product.pricing']._get_first_suitable_pricing(optional_template).recurrence_id:
                    raise UserError(_('You cannot have a optional product that has a different default pricing.'))

    def _website_can_be_added(self, so=None, pricelist=None, pricing=None, product=None):
        """ Return true if the product/template can be added to the active SO
        """
        if not self.recurring_invoice:
            return True
        website = self.env['website'].get_current_website()
        so = so or website and request and website.sale_get_order()
        if not so or not so.recurrence_id or not so.order_line.pricing_id.recurrence_id:
            return True
        if not pricing:
            pricelist = pricelist or website.get_current_pricelist()
            pricing = pricing or self.env['product.pricing']._get_first_suitable_pricing(product or self, pricelist)
        return so.recurrence_id == pricing.recurrence_id

    def _get_first_suitable_pricing_values(self, pricelist, product=None):
        """ Return the value of the first suitable pricing according to the pricelist
        """
        product = product or self
        pricing = self.env['product.pricing']._get_first_suitable_pricing(product, pricelist)
        if not pricing:
            return {
                'is_subscription': True,
                'is_recurrence_possible': False,
            }

        unit_price = pricing.price

        if self.env.context.get('website_id'):
            website = self.env['website'].get_current_website()
            # compute taxes
            partner = self.env.user.partner_id
            company_id = website.company_id
            pricelist = pricelist or website.get_current_pricelist()

            fpos = self.env['account.fiscal.position'].sudo()._get_fiscal_position(partner)
            product_taxes = self.sudo().taxes_id.filtered(lambda t: t.company_id == company_id)
            taxes = fpos.map_tax(product_taxes)
            unit_price = self._price_with_tax_computed(
                unit_price, product_taxes, taxes, company_id, pricelist, product, partner
            )

        if pricelist and pricelist.currency_id != pricing.currency_id:
            company_id = pricing.company_id or self.env.company
            unit_price = pricing.currency_id._convert(unit_price, pricelist.currency_id, company_id, fields.Date.today())

        return {
            'is_subscription': True,
            'price': unit_price,
            'price_reduce': unit_price,
            'is_recurrence_possible': self._website_can_be_added(pricelist=pricelist, pricing=pricing, product=product),
            'subscription_duration': pricing.recurrence_id.duration,
            'subscription_unit': pricing.recurrence_id.unit,
        }

    def _get_combination_info(
            self, combination=False, product_id=False, add_qty=1, pricelist=False,
            parent_combination=False, only_template=False
    ):
        """Override to add the information about subscription for recurring products

        If the product is recurring_invoice, this override adds the following information about the subscription :
            - is_subscription: Whether combination create a subscription,
            - subscription_duration: The recurrence duration
            - subscription_unit: The recurrence unit
            - price: The recurring price
        """
        self.ensure_one()

        combination_info = super()._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template
        )

        if self.recurring_invoice:
            product = self.env['product.product'].browse(combination_info['product_id'])
            combination_info.update(self._get_first_suitable_pricing_values(pricelist, product))
        else:
            combination_info.update(is_subscription=False)
        return combination_info

    # Search bar
    def _search_render_results_prices(self, mapping, combination_info):
        if not combination_info['is_subscription']:
            return super()._search_render_results_prices(mapping, combination_info)

        return self.env['ir.ui.view']._render_template(
            'website_sale_subscription.subscription_search_result_price',
            values={
                'currency': mapping['detail']['display_currency'],
                'price': combination_info['price'],
                'duration': combination_info['subscription_duration'],
                'unit': combination_info['subscription_unit'],
            }
        ), 0

    def _get_sales_prices(self, pricelist):
        prices = super()._get_sales_prices(pricelist)

        for template in self:
            if not template.recurring_invoice:
                continue
            prices[template.id].update(template._get_first_suitable_pricing_values(pricelist))
        return prices

    def _website_show_quick_add(self):
        self.ensure_one()
        return super()._website_show_quick_add() and self._website_can_be_added()

    def _can_be_added_to_cart(self):
        self.ensure_one()
        return super()._can_be_added_to_cart() and self._website_can_be_added()
