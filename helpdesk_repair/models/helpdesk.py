# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    repairs_count = fields.Integer('Repairs Count', compute='_compute_repairs_count', compute_sudo=True)
    repair_ids = fields.One2many('repair.order', 'ticket_id', string='Repairs', copy=False)

    @api.depends('repair_ids')
    def _compute_repairs_count(self):
        repair_data = self.env['repair.order'].sudo().read_group([('ticket_id', 'in', self.ids)], ['ticket_id'], ['ticket_id'])
        mapped_data = dict([(r['ticket_id'][0], r['ticket_id_count']) for r in repair_data])
        for ticket in self:
            ticket.repairs_count = mapped_data.get(ticket.id, 0)

    def action_view_repairs(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Repairs'),
            'res_model': 'repair.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.repair_ids.ids)],
            'context': dict(self._context, create=False, default_company_id=self.company_id.id, default_ticket_id=self.id),
        }
        if self.repairs_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.repair_ids.id
            })
        return action


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    repairs_count = fields.Integer('Repairs Count', compute='_compute_repairs_count')

    def _compute_repairs_count(self):
        repair_data = self.env['repair.order'].sudo().read_group([
            ('ticket_id', 'in', self.ticket_ids.ids),
            ('state', 'not in', ['done', 'cancel'])
        ], ['ticket_id'], ['ticket_id'])
        mapped_data = dict([(r['ticket_id'][0], r['ticket_id_count']) for r in repair_data])
        for team in self:
            team.repairs_count = sum([val for key, val in mapped_data.items() if key in team.ticket_ids.ids])

    def action_view_repairs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")
        repair_ids = self.ticket_ids.repair_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
        if len(repair_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': repair_ids.id,
                'views': [(False, 'form')],
            })
        action.update({
            'domain': [('ticket_id', 'in', repair_ids.mapped('ticket_id.id'))],
            'context': {'create': False},
        })
        return action
