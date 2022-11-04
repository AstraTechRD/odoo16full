# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from .fedex_locations_request import FEDEXLocationsRequest


class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    fedex_use_locations = fields.Boolean(string='Use Fedex Locations', help='Allows the ecommerce user to choose a pick-up point as delivery address.')
    fedex_locations_radius_value = fields.Integer(string='Locations Radius', help='Maximum locations distance radius.', default=15, required=True)
    fedex_locations_radius_unit = fields.Selection(string='Locations Distance Unit', selection=[('KM', 'km'), ('MI', 'mi')], default='KM', required=True)

    def _fedex_get_close_locations(self, partner_address):
        superself = self.sudo()
        srm = FEDEXLocationsRequest(self.log_xml, request_type="locs", prod_environment=self.prod_environment)
        srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
        srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)
        srm.transaction_detail('Location Request partner_id=%d' % partner_address.id)
        srm.set_locs_details(self, partner_address)
        return srm.process_locs()

    def _fedex_update_srm(self, srm, request_type, order=None, picking=None):
        """Add alternate delivery address to the shipment."""
        res = super(ProviderFedex, self)._fedex_update_srm(srm, picking, order)
        if picking:
            order = picking.sale_id
        if order and order.fedex_access_point_address:
            fedex_location = order.get_fedex_access_point_address()
            fedex_loc_details = fedex_location.get('LocationDetail', {})

            hold_at_loc = srm.factory.HoldAtLocationDetail()
            hold_at_loc.PhoneNumber = order.partner_shipping_id.phone
            hold_at_loc.LocationContactAndAddress = fedex_loc_details.get('LocationContactAndAddress', {})
            del hold_at_loc.LocationContactAndAddress['AddressAncillaryDetail']
            hold_at_loc.LocationType = fedex_loc_details.get('LocationType')
            hold_at_loc.LocationId = fedex_loc_details.get('LocationId')

            srm.RequestedShipment.SpecialServicesRequested.HoldAtLocationDetail = hold_at_loc
        return res
