# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.osv import expression



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    unspsc_code_id = fields.Many2one('product.unspsc.code', 'UNSPSC Category', domain=[('applies_to', '=', 'product')],
        help='The UNSPSC code related to this product.  Used for edi in Colombia, Peru and Mexico')


class UomUom(models.Model):
    _inherit = 'uom.uom'

    unspsc_code_id = fields.Many2one('product.unspsc.code', 'UNSPSC Category',
                                                domain=[('applies_to', '=', 'uom')],
                                                help='The UNSPSC code related to this UoM. ')


class ProductCode(models.Model):
    """Product and UoM codes defined by UNSPSC
    Used by Mexico, Peru and Colombia localizations
    """
    _name = 'product.unspsc.code'
    _description = "Product and UOM Codes from UNSPSC"
    _rec_names_get = ['name', 'code']

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)
    applies_to = fields.Selection([('product', 'Product'), ('uom', 'UoM'),], required=True,
        help='Indicate if this code could be used in products or in UoM',)
    active = fields.Boolean()

    def name_get(self):
        result = []
        for prod in self:
            result.append((prod.id, "%s %s" % (prod.code, prod.name or '')))
        return result
