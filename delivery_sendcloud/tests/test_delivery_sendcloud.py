import json
from contextlib import contextmanager
from unittest.mock import patch
import requests

from odoo.tests import TransactionCase, tagged
from odoo import Command

@contextmanager
def _mock_sendcloud_call(warehouse_id):
    def _mock_request(*args, **kwargs):
        method = kwargs.get('method') or args[0]
        url = kwargs.get('url') or args[1]
        responses = {
            'get': {
                'shipping_methods': {'shipping_methods': [{'id': 8, 'name': 'test letter', 'min_weight': 0, 'max_weight': 20}]},
                'shipping-price': [{'price': '5.5', 'currency': 'EUR'}],
                'addresses': {'sender_addresses': [{'contact_name': warehouse_id.name, 'id': 1}]},
                'label': 'mock',
            },
            'post': {
                'parcels': {
                    'parcels': [{
                        'tracking_number': '123',
                        'tracking_url': 'url',
                        'id': 1, 'weight': 10.0,
                        'shipment': {'id': 8},
                        'documents': [{'link': '/label', 'type': 'label'}]
                    }],
                    'status': 'deleted'
                },
            }
        }

        for endpoint, content in responses[method].items():
            if endpoint in url:
                response = requests.Response()
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('unhandled request url %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield

@tagged('-standard', 'external')
class TestDeliverySendCloud(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.your_company = cls.env.ref("base.main_partner")
        cls.warehouse_id = cls.env['stock.warehouse'].search([('company_id', '=', cls.your_company.id)], limit=1)
        cls.your_company.write({'name': 'Odoo SA',
                                'country_id': cls.env.ref('base.be').id,
                                'street': 'Chaussée de Namur 40',
                                'street2': False,
                                'state_id': False,
                                'city': 'Ramillies',
                                'zip': 1367,
                                'phone': '081813700',
                                })
        # deco_art will be in europe
        cls.eu_partner = cls.env.ref('base.res_partner_2')
        cls.eu_partner.write({
            'country_id': cls.env.ref('base.nl').id,
            'zip': '1105AA',
            'state_id': False
        })
        # partner in us (azure)
        cls.us_partner = cls.env.ref('base.res_partner_12')

        cls.product_to_ship1 = cls.env["product.product"].create({
            'name': 'Door with wings',
            'type': 'consu',
            'weight': 10.0
        })

        cls.product_to_ship2 = cls.env["product.product"].create({
            'name': 'Door with Legs',
            'type': 'consu',
            'weight': 15.0
        })

        shipping_product = cls.env['product.product'].create({
            'name': 'SendCloud Delivery',
            'type': 'service'
        })

        cls.sendcloud = cls.env['delivery.carrier'].create({
            'delivery_type': 'sendcloud',
            'product_id': shipping_product.id,
            'sendcloud_public_key': 'mock_key',
            'sendcloud_secret_key': 'mock_key',
            'name': 'SendCloud'
        })
        with _mock_sendcloud_call(cls.warehouse_id):
            wiz_action = cls.sendcloud.action_load_sendcloud_shipping_products()
            wiz = cls.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
                'shipping_product': next(iter(wiz_action['context']['shipping_products'].keys()), False),  # choose first of shipping methods found
                'carrier_id': cls.sendcloud.id
            })
            wiz.action_validate()

    def test_deliver_inside_eu(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.eu_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id
                })
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.sendcloud.id,
            'order_id': sale_order.id
        })
        with _mock_sendcloud_call(self.warehouse_id):
            # dont assert price since unstamped letter has a price of 0
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")
            picking.action_assign()
            picking.action_set_quantities_to_reservation()
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.sendcloud_parcel_ref, False,
                             "SendCloud Parcel Id not set")

    def test_deliver_outside_eu(self):
        '''
            Same workflow as inside EU but tests other inner workings of sendcloud service
        '''
        sale_order = self.env['sale.order'].create({
            'partner_id': self.us_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id
                })
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.sendcloud.id,
            'order_id': sale_order.id
        })
        with _mock_sendcloud_call(self.warehouse_id):
            # dont assert price since unstamped letter has a price of 0
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for ups shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")
            picking.action_assign()
            picking.action_set_quantities_to_reservation()
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.sendcloud_parcel_ref, False,
                             "SendCloud Parcel Id not set")
