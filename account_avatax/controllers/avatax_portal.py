# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.addons.account.controllers.portal import CustomerPortal


class AvataxCustomerPortal(CustomerPortal):
    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        response = super(AvataxCustomerPortal, self).portal_my_invoice_detail(
            invoice_id,
            access_token=access_token,
            report_type=report_type,
            download=download,
            **kw
        )
        if 'invoice' not in response.qcontext:
            return response

        invoice = response.qcontext['invoice']
        if invoice.state == 'draft' and invoice.fiscal_position_id.is_avatax:
            invoice.button_update_avatax()

        return response
