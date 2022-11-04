# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request


class EventBarcode(http.Controller):

    @http.route(['/event/init_barcode_interface'], type='json', auth="user")
    def init_barcode_interface(self, event_id):
        event = request.env['event.event'].browse(event_id).exists() if event_id else False
        if event:
            return {
                'name': event.name,
                'country': event.address_id.country_id.name,
                'city': event.address_id.city,
                'company_name': event.company_id.name,
                'company_id': event.company_id.id
            }
        else:
            return {
                'name': _('Registration Desk'),
                'country': False,
                'city': False,
                'company_name': request.env.company.name,
                'company_id': request.env.company.id
            }
