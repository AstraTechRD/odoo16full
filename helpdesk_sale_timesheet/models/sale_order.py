# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ticket_count = fields.Integer(string='Ticket Count', compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        if not self.env.user.has_group('helpdesk.group_helpdesk_user'):
            self.ticket_count = 0
            return

        ticket_data = self.env['helpdesk.ticket'].read_group([
            '|', ('sale_order_id', 'in', self.ids),
            ('sale_line_id', 'in', self.order_line.ids),
            ('use_helpdesk_sale_timesheet', '=', True)
        ], ['sale_order_id'], ['sale_order_id'])
        mapped_data = dict((data['sale_order_id'][0], data['sale_order_id_count']) for data in ticket_data)
        for so in self:
            so.ticket_count = mapped_data.get(so.id, 0)

    def action_confirm(self):
        res = super().action_confirm()
        for sla in self.mapped('order_line.product_template_id.sla_id'):
            order_lines = self.order_line.filtered(lambda x: x.product_template_id.sla_id == sla)
            sla.write({
                'sale_line_ids': [Command.link(l.id) for l in order_lines],
            })
        return res

    def action_view_tickets(self):
        action = self.env["ir.actions.actions"]._for_xml_id('helpdesk.helpdesk_ticket_action_main_tree')
        if self.ticket_count == 1:
            ticket = self.env['helpdesk.ticket'].search(['|', ('sale_order_id', '=', self.id), ('sale_line_id', 'in', self.order_line.ids)], limit=1)
            action.update({
                'view_mode': 'form',
                'res_id': ticket.id,
                'views': [(False, 'form')],
            })
        service_lines = self.order_line.filtered(lambda x: x.product_id.type == 'service')
        action.update({
            'domain': ['|', ('sale_order_id', '=', self.id), ('sale_line_id', 'in', self.order_line.ids)],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_sale_line_id': service_lines and service_lines[0].id,
            }
        })
        return action
