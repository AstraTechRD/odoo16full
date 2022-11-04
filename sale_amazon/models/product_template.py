# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    offer_count = fields.Integer(
        compute='_compute_offer_count', groups='sales_team.group_sale_manager'
    )

    def _compute_offer_count(self):
        offers_data = self.env['amazon.offer'].read_group(
            [('product_template_id', 'in', self.ids)],
            ['product_template_id'],
            ['product_template_id'],
        )
        product_templates_data = {
            offer_data['product_template_id'][0]: offer_data['product_template_id_count']
            for offer_data in offers_data
        }
        for product_template in self:
            product_template.offer_count = product_templates_data.get(product_template.id, 0)

    def action_view_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Offers'),
            'res_model': 'amazon.offer',
            'view_mode': 'tree,form',
            'context': {'create': False},
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
        }
