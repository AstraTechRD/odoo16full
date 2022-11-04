import json
from odoo import http
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.exceptions import UserError
from odoo.http import request


class WebsiteSaleDeliveryFedex(WebsiteSaleDelivery):
    @http.route('/shop/fedex_access_point/set', type='json', auth='public', methods=['POST'], csrf=False, website=True, sitemap=False)
    def set_fedex_access_point(self, **post):
        order = request.website.sale_get_order()
        access_point = order.carrier_id.fedex_use_locations and post.get('access_point_encoded') or None
        order.write({'fedex_access_point_address': access_point})

    @http.route('/shop/fedex_access_point/get', type='json', auth='public', csrf=False, website=True, sitemap=False)
    def get_fedex_access_point(self, **post):
        order = request.website.sale_get_order()
        fedex_order_location = order.get_fedex_access_point_address()
        if fedex_order_location:
            address = fedex_order_location['LocationDetail']['LocationContactAndAddress']['Address']
            return {'fedex_access_point': '%s, %s (%s)' % (', '.join(address['StreetLines']), address['City'], address['PostalCode'])}
        return {}

    @http.route('/shop/fedex_access_point/close_locations', type='json', auth='public', csrf=False, website=True, sitemap=False)
    def get_fedex_close_locations(self, **post):
        order = request.website.sale_get_order()
        try:
            close_locations = order.carrier_id._fedex_get_close_locations(order.partner_shipping_id)
            partner_address = order.partner_shipping_id
            inline_partner_address = ' '.join((part or '') for part in [partner_address.street, partner_address.street2, partner_address.zip, partner_address.country_id.code])
            for location in close_locations:
                location['stringified'] = json.dumps(location)
            return {'close_locations': close_locations, 'partner_address': inline_partner_address}
        except UserError as e:
            return {'error': str(e)}
