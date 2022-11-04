# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_combination_info(
        self, combination=False, product_id=False, add_qty=1, pricelist=False,
        parent_combination=False, only_template=False
    ):
        """Override to improve information about rental product stock.

        Free quantity of rental product is the minimal amount of available quantities during the
        given period.
        """
        self.ensure_one()

        combination_info = super()._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template
        )

        if not self.env.context.get('website_sale_stock_get_quantity'):
            return combination_info

        if self.rent_ok and combination_info['product_id'] and not self.allow_out_of_stock_order:
            start_date = self.env.context.get('start_date')
            end_date = self.env.context.get('end_date')
            if end_date and start_date:
                product = self.env['product.product'].sudo().browse(combination_info['product_id'])
                warehouse_id = self.env['website'].get_current_website()._get_warehouse_available()
                combination_info['free_qty'] = min(
                    avail['quantity_available']
                    for avail in product._get_availabilities(start_date, end_date, warehouse_id)
                )
        return combination_info

    def _get_default_start_date(self):
        """ Override to take the padding time into account """
        if self.preparation_time > 24:
            return self._get_first_potential_date(
                fields.Datetime.now() + relativedelta(
                    hours=self.preparation_time, minute=0, second=0, microsecond=0
                )
            )
        return super()._get_default_start_date()

    def _filter_on_available_rental_products(self, from_date, to_date, warehouse_id):
        """
        Filters self on available record for the given period.

        It will return true if any variant has an available stock.
        """
        self = self.with_context(from_date=from_date, to_date=to_date, warehouse_id=warehouse_id)

        if to_date < from_date:
            return self.filtered(lambda p: not p.rent_ok)

        products_infinite_qty = products_finite_qty = self.env['product.template']
        for product in self:
            if not product.rent_ok or product.type != 'product' or product.allow_out_of_stock_order:
                products_infinite_qty |= product
            else:
                products_finite_qty |= product

        # Prefetch qty_available for all variants
        variants_to_check = products_finite_qty.product_variant_ids.filtered("qty_available")
        templates_with_available_qty = self.env['product.template']
        if variants_to_check:
            sols = self.env['sale.order.line'].search(
                [
                    ('is_rental', '=', True),
                    ('product_id', 'in', variants_to_check.ids),
                    ('state', 'in', ('sent', 'sale', 'done')),
                    ('return_date', '>', from_date),
                    ('reservation_begin', '<', to_date),
                ],
                order="reservation_begin asc"
            )
            # Group SOL by product_id
            sol_by_variant = defaultdict(lambda: self.env['sale.order.line'])
            for sol in sols:
                sol_by_variant[sol.product_id] |= sol

            def has_any_available_qty(variant, sols):
                # Returns False if the rented quantity was higher or equal to the available qty at any point in time.
                rented_quantities, key_dates = sols._get_rented_quantities([from_date, to_date])
                max_rentable = variant.qty_available
                for date in key_dates:
                    max_rentable -= rented_quantities[date]
                    if max_rentable <= 0:
                        return False
                return True

            templates_with_available_qty = variants_to_check.filtered(
                lambda v: v not in sol_by_variant or has_any_available_qty(v, sol_by_variant[v])
            ).product_tmpl_id

        return products_infinite_qty | templates_with_available_qty
