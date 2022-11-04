# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, _lt

class Project(models.Model):
    _inherit = 'project.project'

    ticket_ids = fields.One2many('helpdesk.ticket', 'project_id', string='Tickets')
    ticket_count = fields.Integer('# Tickets', compute='_compute_ticket_count')

    helpdesk_team = fields.One2many('helpdesk.team', 'project_id')
    has_helpdesk_team = fields.Boolean('Has Helpdesk Teams', compute='_compute_has_helpdesk_team', compute_sudo=True)

    @api.depends('ticket_ids.project_id')
    def _compute_ticket_count(self):
        if not self.user_has_groups('helpdesk.group_helpdesk_user'):
            self.ticket_count = 0
            return
        result = self.env['helpdesk.ticket'].read_group([
            ('project_id', 'in', self.ids)
        ], ['project_id'], ['project_id'])
        data = {data['project_id'][0]: data['project_id_count'] for data in result}
        for project in self:
            project.ticket_count = data.get(project.id, 0)

    @api.depends('helpdesk_team.project_id')
    def _compute_has_helpdesk_team(self):
        result = self.env['helpdesk.team'].read_group([
            ('project_id', 'in', self.ids)
        ], ['project_id'], ['project_id'])
        data = {data['project_id'][0]: data['project_id_count'] > 0 for data in result}
        for project in self:
            project.has_helpdesk_team = data.get(project.id, False)

    def action_open_project_tickets(self):
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_timesheet.project_project_action_view_helpdesk_tickets")
        action.update({
            'display_name': _('Tickets'),
            'domain': [('id', 'in', self.ticket_ids.ids)],
            'context': {'active_id': self.id},
        })
        if len(self.ticket_ids.ids) == 1:
            action["view_mode"] = 'form'
            action["views"] = [[False, 'form']]
            action["res_id"] = self.ticket_ids.id
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'life-ring',
            'text': _lt('Tickets'),
            'number': self.ticket_count,
            'action_type': 'object',
            'action': 'action_open_project_tickets',
            'show': self.ticket_count > 0,
            'sequence': 51,
        })
        return buttons
