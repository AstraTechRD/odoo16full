# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rent_ok = fields.Boolean(
        string="Can be Rented",
        help="Allow renting of this product.")
    qty_in_rent = fields.Float("Quantity currently in rent", compute='_get_qty_in_rent')

    # Delays pricing

    extra_hourly = fields.Float("Extra Hour", help="Fine by hour overdue", company_dependent=True)
    extra_daily = fields.Float("Extra Day", help="Fine by day overdue", company_dependent=True)

    @api.model
    def _get_incompatible_types(self):
        return ['rent_ok'] + super()._get_incompatible_types()

    @api.constrains('rent_ok')
    def _prevent_renting_incompability(self):
        """ Some boolean fields are incompatibles """
        self._check_incompatible_types()

    @api.depends('rent_ok')
    def _compute_is_temporal(self):
        super()._compute_is_temporal()
        self.filtered('rent_ok').is_temporal = True

    def _compute_visible_qty_configurator(self):
        super(ProductTemplate, self)._compute_visible_qty_configurator()
        for product_template in self:
            if len(product_template.product_variant_ids) > 1 and product_template.rent_ok:
                product_template.visible_qty_configurator = False

    def _get_qty_in_rent(self):
        rentable = self.filtered('rent_ok')
        not_rentable = self - rentable
        not_rentable.update({'qty_in_rent': 0.0})
        for template in rentable:
            template.qty_in_rent = sum(template.mapped('product_variant_ids.qty_in_rent'))

    def action_view_rentals(self):
        """Access Gantt view of rentals (sale.rental.schedule), filtered on variants of the current template."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Scheduled Rentals"),
            "res_model": "sale.rental.schedule",
            "views": [[False, "gantt"]],
            'domain': [('product_id', 'in', self.mapped('product_variant_ids').ids)],
            'context': {
                'search_default_Rentals':1,
                'group_by_no_leaf':1,
                'group_by':[],
                'restrict_renting_products': True,
            }
        }

    def name_get(self):
        res_names = super(ProductTemplate, self).name_get()
        if not self._context.get('rental_products'):
            return res_names
        return [
            (res[0], self.browse(res[0]).rent_ok and _("%s (Rental)", res[1]) or res[1])
            for res in res_names
        ]

    def _get_contextual_price(self, product=None):
        self.ensure_one()
        if not (product or self).rent_ok:
            return super()._get_contextual_price(product=product)

        pricelist = self._get_contextual_pricelist()
        if not pricelist:
            return 0.0

        quantity = self.env.context.get('quantity', 1.0)
        uom = self.env['uom.uom'].browse(self.env.context.get('uom'))
        date = self.env.context.get('date')
        start_date = self.env.context.get('start_date')
        end_date = self.env.context.get('end_date')
        return pricelist._get_product_price(
            product or self, quantity, uom=uom, date=date, start_date=start_date, end_date=end_date
        )

    def _can_be_added_to_cart(self):
        """Override to allow rental products to be used in a sale order"""
        return super()._can_be_added_to_cart() or self.rent_ok
