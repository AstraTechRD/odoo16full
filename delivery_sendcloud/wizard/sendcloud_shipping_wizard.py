# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api

class SendCloudShippingWizard(models.TransientModel):

    _name = "sendcloud.shipping.wizard"
    _description = "Choose from the available sendcloud shipping methods"

    carrier_id = fields.Many2one('delivery.carrier', string="Delivery")

    shipping_product = fields.Selection(selection="_compute_shipping_products", string="Shipping Product", required=True)
    ship_carrier = fields.Char(compute="_compute_ship_carrier", string="Carrier")
    ship_min_weight = fields.Float(string="Minimum Weight", compute="_compute_ship_carrier")
    ship_max_weight = fields.Float(string="Maximum Weight", compute="_compute_ship_carrier")
    ship_country_ids = fields.Many2many('res.country', compute="_compute_ship_carrier", string="Countries")
    # Return Shipment Info
    return_product = fields.Selection(selection="_compute_return_products", string="Return Shipping Product")
    return_carrier = fields.Char(compute="_compute_return_carrier", string="Return Carrier")
    return_min_weight = fields.Float(string="Return Minimum Weight", compute="_compute_return_carrier")
    return_max_weight = fields.Float(string="Return Maximum Weight", compute="_compute_return_carrier")
    return_country_ids = fields.Many2many('res.country', compute="_compute_return_carrier", string="Return Countries")

    def _compute_shipping_products(self):
        shipping_products = self.env.context.get('shipping_products', {})
        return [(ship_id, ship['name']) for ship_id, ship in shipping_products.items()]

    def _compute_return_products(self):
        return_products = self.env.context.get('return_products', [])
        return [(ship_id, ship['name']) for ship_id, ship in return_products.items()]

    @api.depends('shipping_product')
    def _compute_ship_carrier(self):
        for rec in self:
            product = self._get_product_from_ctx(rec.shipping_product)
            country_codes = [country['iso_2'] for country in product.get('countries', [])]
            rec.ship_carrier = product.get('carrier', False)
            rec.ship_min_weight = product.get('min_weight', False)
            rec.ship_max_weight = product.get('max_weight', False)
            rec.ship_country_ids = self.env['res.country'].search([('code', 'in', country_codes)])

    @api.depends('return_product')
    def _compute_return_carrier(self):
        for rec in self:
            product = self._get_product_from_ctx(rec.return_product, is_return=True)
            country_codes = [country['iso_2'] for country in product.get('countries', [])]
            rec.return_carrier = product.get('carrier', False)
            rec.return_min_weight = product.get('min_weight', False)
            rec.return_max_weight = product.get('max_weight', False)
            rec.return_country_ids = self.env['res.country'].search([('code', 'in', country_codes)])

    def _get_product_from_ctx(self, prod_id, is_return=False):
        products = 'shipping_products' if not is_return else 'return_products'
        ship_products = self.env.context.get(products, {})
        return ship_products.get(prod_id, {})

    def action_validate(self):
        for rec in self:
            # delete old shipping product since it will be replaced
            rec.carrier_id.sendcloud_shipping_id.unlink()
            shipping_product_name = dict(self._compute_shipping_products()).get(rec.shipping_product)
            products_to_create = [{
                'name': shipping_product_name,
                'sendcloud_id': rec.shipping_product,
                'carrier': rec.ship_carrier,
                'min_weight': rec.ship_min_weight,
                'max_weight': rec.ship_max_weight,
            }]
            if rec.return_product:
                rec.carrier_id.sendcloud_return_id.sudo().unlink()
                shipping_product_name = dict(self._compute_return_products()).get(rec.return_product)
                products_to_create.append({
                    'name': shipping_product_name,
                    'sendcloud_id': rec.return_product,
                    'carrier': rec.return_carrier,
                    'min_weight': rec.return_min_weight,
                    'max_weight': rec.return_max_weight,
                })
            products = self.env['sendcloud.shipping.product'].create(products_to_create)
            if rec.return_product:
                rec.carrier_id.sendcloud_shipping_id = products[0]
                rec.carrier_id.sendcloud_return_id = products[1]
            else:
                rec.carrier_id.sendcloud_shipping_id = products
                rec.carrier_id.sendcloud_return_id = False
