# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.sale_management.controllers.portal import CustomerPortal as CustomerPortalSaleManagement

from odoo import http


class CustomerPortalAvatax(CustomerPortal):
    @http.route([
        '/my/orders/<int:order_id>',
    ], type='http', auth='public', website=True)
    def portal_order_page(self, order_id=None, **post):
        response = super(CustomerPortalAvatax, self).portal_order_page(order_id=order_id, **post)
        if 'sale_order' not in response.qcontext:
            return response

        # Update taxes before customers see their quotation. This also ensures that tax validation
        # works (e.g. customer has valid address, ...). Otherwise errors will occur during quote
        # confirmation.
        order = response.qcontext['sale_order']
        if order.state in ('draft', 'sent') and order.fiscal_position_id.is_avatax:
            order.button_update_avatax()

        return response


class CustomerPortalSaleManagementAvatax(CustomerPortalSaleManagement):
    def _get_order_portal_content(self, order_sudo):
        if order_sudo.fiscal_position_id.is_avatax:
            order_sudo.button_update_avatax()

        return super()._get_order_portal_content(order_sudo)
