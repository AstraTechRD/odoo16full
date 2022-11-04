# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    intrastat_code_id = fields.Many2one(
        'account.intrastat.code',
        related='product_variant_ids.intrastat_code_id',
        string='Commodity Code',
        readonly=False,
    )
    intrastat_supplementary_unit = fields.Selection(related='intrastat_code_id.supplementary_unit')
    intrastat_supplementary_unit_amount = fields.Float(
        related='product_variant_ids.intrastat_supplementary_unit_amount',
        help='The number of supplementary units per product quantity.',
        readonly=False,
    )
    intrastat_origin_country_id = fields.Many2one(
        'res.country',
        related='product_variant_ids.intrastat_origin_country_id',
        string='Country of Origin',
        readonly=False,
    )

class ProductProduct(models.Model):
    _inherit = 'product.product'

    intrastat_code_id = fields.Many2one(comodel_name='account.intrastat.code', string='Commodity code', domain="[('type', '=', 'commodity')]")
    # The supplementary unit of the current commodity code
    intrastat_supplementary_unit = fields.Selection(related='intrastat_code_id.supplementary_unit')
    # The ratio of product to the number of supplementary units
    intrastat_supplementary_unit_amount = fields.Float(
        string='Supplementary Units',
        help='The number of supplementary units per product quantity.',
    )
    intrastat_origin_country_id = fields.Many2one('res.country', string='Country of Origin')

    @api.depends('intrastat_supplementary_unit')
    def _compute_intrastat_supplementary_unit_amount(self):
        """ In the case when the product has no supplementary unit (i.e. we are using weight) the supplementary unit amount is set to 0 """
        for product in self:
            if not product.intrastat_supplementary_unit:
                product.intrastat_supplementary_unit_amount = 0
