# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_in_rent = fields.Float("Quantity currently in rent", compute='_get_qty_in_rent')

    def name_get(self):
        res_names = super(ProductProduct, self).name_get()
        if not self._context.get('rental_products'):
            return res_names
        return [
            (res[0], self.browse(res[0]).rent_ok and _("%s (Rental)", res[1]) or res[1])
            for res in res_names
        ]

    def _get_qty_in_rent_domain(self):
        return [
            ('is_rental', '=', True),
            ('product_id', 'in', self.ids),
            ('state', 'in', ['sale', 'done'])]

    def _get_qty_in_rent(self):
        """
        Note: we don't use product.with_context(location=self.env.company.rental_loc_id.id).qty_available
        because there are no stock moves for services (which can be rented).
        """
        active_rental_lines = self.env['sale.order.line']._read_group(
            domain=self._get_qty_in_rent_domain(),
            fields=['product_id', 'qty_delivered:sum', 'qty_returned:sum'],
            groupby=['product_id'],
        )
        res = dict((data['product_id'][0], data['qty_delivered'] - data['qty_returned']) for data in active_rental_lines)
        for product in self:
            product.qty_in_rent = res.get(product.id, 0)

    def _compute_delay_price(self, duration):
        """Compute daily and hourly delay price.

        :param timedelta duration: datetime representing the delay.
        """
        days = duration.days
        hours = duration.seconds // 3600
        return days * self.extra_daily + hours * self.extra_hourly

    def action_view_rentals(self):
        """Access Gantt view of rentals (sale.rental.schedule), filtered on variants of the current template."""
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.rental.schedule",
            "name": _("Scheduled Rentals"),
            "views": [[False, "gantt"]],
            'domain': [('product_id', 'in', self.ids)],
            'context': {
                'search_default_Rentals':1,
                'group_by_no_leaf':1,
                'group_by':[],
                'restrict_renting_products': True,
            }
        }
