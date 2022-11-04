# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _get_default_so_domain(self, ticket):
        domain = super()._get_default_so_domain(ticket)
        if ticket.product_id:
            domain = expression.AND([
                domain,
                [('order_line.product_id', '=', ticket.product_id.id)]
            ])
        if ticket.sale_line_id:
            domain = expression.AND([
                domain,
                [('order_line', '=', ticket.sale_line_id.id)]
            ])
        return domain

    def _get_suitable_move_domain(self):
        domain = super()._get_suitable_move_domain()
        if self.helpdesk_ticket_id.product_id:
            domain = expression.AND([
                domain,
                [('invoice_line_ids.product_id', '=', self.helpdesk_ticket_id.product_id.id)]
            ])
        return domain

    def _get_suitable_so_domain(self):
        domain = super()._get_suitable_so_domain()
        if self.helpdesk_ticket_id.product_id:
            domain = expression.AND([
                domain,
                [('order_line.product_id', '=', self.helpdesk_ticket_id.product_id.id)]
            ])
        return domain
