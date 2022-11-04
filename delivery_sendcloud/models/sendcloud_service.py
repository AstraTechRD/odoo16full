# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import math
import requests
from werkzeug.urls import url_join


from odoo import fields, _
from odoo.exceptions import UserError

BASE_URL = "https://panel.sendcloud.sc/api/v2/"

class SendCloud:

    def __init__(self, public_key, private_key, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.auth = (public_key, private_key)

    def get_shipping_products(self, is_return=False):
        res = self._send_request('shipping_methods', params={'is_return': is_return})
        shipping_products = res.get('shipping_methods', [])
        return {ship['id']: ship for ship in shipping_products}

    def get_shipping_rate(self, carrier, order=None, picking=None, parcel=None):
        # Get source, destination and weight
        if order:
            to_country = order.partner_shipping_id.country_id.code
            from_country = order.warehouse_id.partner_id.country_id.code
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                raise UserError(_("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s") % ", ".join(error_lines.product_id.mapped('name')))
            packages = carrier._get_packages_from_order(order, carrier.sendcloud_default_package_type_id)
            total_weight = sum(pack.weight for pack in packages)
        elif picking:
            to_country = picking.destination_country_code
            from_country = picking.location_id.warehouse_id.partner_id.country_id.code
            total_weight = float(parcel['weight'])
        else:
            raise UserError(_('No picking or order provided'))
        if not to_country or not from_country:
            raise UserError(_('Make sure country codes are set in partner country and warehouse country'))
        # Get Shipping Id
        shipping_id = parcel.get('shipment', {}).get('id') if parcel else carrier.sendcloud_shipping_id.sendcloud_id
        if not shipping_id:
            carrier.raise_redirect_message()
        # if the weight is greater than max weight and source is order (initial estimate)
        # split the weight into packages instead of returning no price / offer
        packages_no = 0
        total_weight = float(carrier.sendcloud_convert_weight(total_weight))
        if total_weight > carrier.sendcloud_shipping_id.max_weight and order:
            packages_no = math.ceil(total_weight / carrier.sendcloud_shipping_id.max_weight)
            # max weight from sendcloud is 1 gram extra (eg. if max allowed weight = 3kg, sendcloud_shipping_id.max_weight = 3.001 kg)
            total_weight = carrier.sendcloud_shipping_id.max_weight - 0.001
        # Convert Weight to sendcloud weight (grams)
        # this endpoint expects integer for weight so to prevent loss in weight we use grams
        total_weight = int(carrier.sendcloud_convert_weight(total_weight, grams=True))
        params = {
            'shipping_method_id': shipping_id,
            'to_country': to_country,
            'from_country': from_country,
            'weight': total_weight,
            'weight_unit': 'gram'
        }
        price = self._send_request('shipping-price', params=params)

        if not price:
            raise UserError(_('The selected shipping method does not ship from %s to %s', from_country, to_country))
        # the API response is an Array of 1 dict with price and currency (usually EUR)
        price = price[0]
        currency = price.get('currency')
        price = price.get('price')
        # shipping id 8 is a test shipping and does not provide a price, but we still need the flow to continue
        # the check is done after the request since in the future if price is actually returned it will be passed correctly
        if shipping_id == 8 and price is None:
            return 0.0, 0
        if price is None:
            raise UserError(_('There is no rate available for this order with the selected shipping method'))
        price = float(price)
        if packages_no:
            price *= packages_no
        currency_id = carrier.env['res.currency'].with_context(active_test=False).search([('name', '=', currency)])
        if not currency_id:
            raise UserError(_('Could not find currency %s', currency))

        to_currency_id = order.currency_id if order else picking.sale_id.currency_id
        converted_price = currency_id._convert(price, to_currency_id, carrier.env.company, fields.Date.context_today(carrier))
        return converted_price, packages_no

    def send_shipment(self, picking, is_return=False):
        sender_id = None
        if not is_return:
            # get warehouse for each picking and get the sender address to use for shipment
            sender_id = self._get_pick_sender_address(picking)
        parcels = self._prepare_parcel(picking, sender_id, is_return)
        data = {
            'parcels': parcels
        }
        res = self._send_request('parcels', 'post', data, params={'errors': 'verbose-carrier'})
        res_parcels = res.get('parcels')
        if not res_parcels:
            raise UserError('Something went wrong, parcel not returned from Sendcloud')
        return res_parcels

    def track_shipment(self, parcel_id):
        parcel = self._send_request(f'parcels/{parcel_id}')
        return parcel['parcel']

    def cancel_shipment(self, parcel_id):
        res = self._send_request(f'parcels/{parcel_id}/cancel', method='post')
        return res

    def get_document(self, url):
        ''' Returns pdf content of document to print '''
        self.logger(f'get {url}', 'sendcloud get document')
        try:
            res = self.session.request(method='get', url=url, timeout=15)
        except Exception as err:
            self.logger(str(err), f'sendcloud response {url}')
            raise UserError(_('Something went wrong, please try again later!!'))

        self.logger(f'{res.content}', 'sendcloud get document response')
        if res.status_code != 200:
            raise UserError(_('Could not get document!'))
        return res.content

    def get_addresses(self):
        res = self._send_request('user/addresses/sender')
        return res.get('sender_addresses', [])

    def _send_request(self, endpoint, method='get', data=None, params=None):
        url = url_join(BASE_URL, endpoint)
        self.logger(f'{url}\n{method}\n{data}', f'sendcloud request {endpoint}')
        if method not in ['get', 'post']:
            raise Exception(f'Unhandled request method {method}')
        try:
            res = self.session.request(method=method, url=url, json=data, params=params, timeout=15)
            self.logger(f'{res.status_code} {res.text}', f'sendcloud response {endpoint}')
            res = res.json()
        except Exception as err:
            self.logger(str(err), f'sendcloud response {endpoint}')
            raise UserError(_('Something went wrong, please try again later!!'))

        if 'error' in res:
            raise UserError(res['error']['message'])
        return res

    def _prepare_parcel_items(self, pkg, carrier):
        parcel_items = []
        for commodity in pkg.commodities:
            hs_code = commodity.product_id.hs_code or ''
            for ch in [' ', '.']:
                if ch in hs_code:
                    hs_code = hs_code.replace(ch, '')
            parcel_items.append({
                'description': commodity.product_id.name,
                'quantity': commodity.qty,
                # float_round util function does work well with numbers such as 0.7
                'weight': round(carrier.sendcloud_convert_weight(commodity.product_id.weight), 3),
                'value': round(commodity.monetary_value, 3),
                'hs_code': hs_code[:8],
                'origin_country': commodity.country_of_origin or '',
                'sku': commodity.product_id.barcode or '',
            })
        return parcel_items

    def _get_house_number(self, address):
        house_number = re.findall(r"([1-9]+\w*)", address)
        if house_number:
            return house_number[0]
        return ' '

    def _validate_partner_details(self, partner):
        if not partner.phone:
            raise UserError(_('%(partner_name)s phone required', partner_name=partner.name))
        if not partner.email:
            raise UserError(_('%(partner_name)s email required', partner_name=partner.name))
        if not all([partner.street, partner.city, partner.zip, partner.country_id]):
            raise UserError(_('The %s address needs to have the street, city, zip, and country', partner.name))

    def _prepare_parcel(self, picking, sender_id, is_return):
        to_partner_id = picking.partner_id
        from_partner_id = None
        if is_return:
            # picking partner id is now the source and the destination is the warehouse partner id
            to_partner_id = picking.picking_type_id.warehouse_id.partner_id
            from_partner_id = picking.partner_id
        # if a return label will be generated and this is not the return,
        # make sure all the data needed by the return is there to prevent creating the shipment without the return
        if picking.carrier_id.return_label_on_delivery:
            warehouse_address = picking.picking_type_id.warehouse_id.partner_id
            self._validate_partner_details(warehouse_address)
        self._validate_partner_details(to_partner_id)
        # get shipment id and check to apply sendcloud rules or not
        if not is_return:
            shipment_id = picking.carrier_id.sendcloud_shipping_id.sendcloud_id
            if not shipment_id:
                picking.carrier_id.raise_redirect_message()
            shipment_name = picking.carrier_id.sendcloud_shipping_id.name
            apply_rules = picking.carrier_id.sendcloud_shipping_rules in ['ship', 'both']
        else:
            if not picking.carrier_id.sendcloud_return_id:
                picking.carrier_id.raise_redirect_message()
            shipment_id = picking.carrier_id.sendcloud_return_id.sendcloud_id
            shipment_name = picking.carrier_id.sendcloud_return_id.name
            apply_rules = picking.carrier_id.sendcloud_shipping_rules in ['return', 'both']
        error_lines = picking.move_ids.filtered(lambda line: not line.weight)
        if error_lines:
            raise UserError(_("The weight of some products is missing: \n %s") % ", ".join(error_lines.product_id.mapped('name')))
        parcels = []
        delivery_packages = picking.carrier_id._get_packages_from_picking(picking, picking.carrier_id.sendcloud_default_package_type_id)
        parcel_common = {
            'name': to_partner_id.name,
            'address': to_partner_id.street,
            'address_2': to_partner_id.street2 or '',
            'house_number': self._get_house_number(to_partner_id.street),
            'city': to_partner_id.city or '',
            'country_state': to_partner_id.state_id.code or '',
            'postal_code': to_partner_id.zip,
            'country': to_partner_id.country_id.code,
            'telephone': to_partner_id.phone or '',
            'email': to_partner_id.email or '',
            'request_label': True,
            'apply_shipping_rules': apply_rules,
            'shipment': {
                'id': shipment_id
            },
            'is_return': is_return,
            'shipping_method_checkout_name': shipment_name,
            'customs_shipment_type': 4 if is_return else 2,
            'customs_invoice_nr': picking.origin or ''
        }
        if sender_id:
            parcel_common.update({
                'sender_address': sender_id
            })
        if from_partner_id:
            self._validate_partner_details(from_partner_id)
            parcel_common.update({
                'from_name': from_partner_id.name,
                'from_house_number': self._get_house_number(from_partner_id.street),
                'from_address_1': from_partner_id.street or '',
                'from_address_2': from_partner_id.street2 or '',
                'from_city': from_partner_id.city or '',
                'from_state': from_partner_id.state_id.code or '',
                'from_postal_code': from_partner_id.zip or '',
                'from_country': from_partner_id.country_id.code,
                'from_telephone': from_partner_id.phone or '',
                'from_email': from_partner_id.email or '',
            })
        for pkg in delivery_packages:
            parcel = dict(parcel_common)
            if not pkg.weight:
                raise UserError(_("Ensure picking has shipping weight, if using packages, each package should have a shipping weight"))
            parcel.update({
                'weight': pkg.weight,
                'length': pkg.dimension['length'],
                'width': pkg.dimension['width'],
                'height': pkg.dimension['height'],
            })
            parcel['parcel_items'] = self._prepare_parcel_items(pkg, picking.carrier_id)
            parcels.append(parcel)
        return parcels

    def _get_pick_sender_address(self, picking):
        warehouse_name = picking.location_id.warehouse_id.name.lower().replace(' ', '')
        addresses = self.get_addresses()
        res_id = None
        for addr in addresses:
            label = addr.get('label', '').lower().replace(' ', '')
            contact_name = addr.get('contact_name', '').lower().replace(' ', '')
            if label == warehouse_name or contact_name == warehouse_name:
                res_id = addr['id']
                break
        if not res_id:
            raise UserError(_('No address found with contact name %s on your sendcloud account.', picking.location_id.warehouse_id.name))
        return res_id
