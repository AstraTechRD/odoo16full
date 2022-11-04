# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket', 'Helpdesk Ticket', index='btree_not_null',
        compute='_compute_helpdesk_ticket_id', store=True, readonly=False,
        domain="[('company_id', '=', company_id), ('project_id', '=?', project_id)]")
    has_helpdesk_team = fields.Boolean(related='project_id.has_helpdesk_team')
    display_task = fields.Boolean(compute="_compute_display_task")

    @api.depends('has_helpdesk_team', 'project_id', 'task_id', 'helpdesk_ticket_id')
    def _compute_display_task(self):
        for line in self:
            line.display_task = line.task_id or not line.has_helpdesk_team

    @api.depends('project_id')
    def _compute_helpdesk_ticket_id(self):
        for line in self:
            if not line.project_id or line.project_id != line.helpdesk_ticket_id.project_id:
                line.helpdesk_ticket_id = False

    @api.constrains('task_id', 'helpdesk_ticket_id')
    def _check_no_link_task_and_ticket(self):
        # Check if any timesheets are not linked to a ticket and a task at the same time
        if any(timesheet.task_id and timesheet.helpdesk_ticket_id for timesheet in self):
            raise ValidationError(_("You cannot link a timesheet entry to a task and a ticket at the same time."))

    @api.depends('helpdesk_ticket_id.partner_id')
    def _compute_partner_id(self):
        super(AccountAnalyticLine, self)._compute_partner_id()
        for line in self:
            if line.helpdesk_ticket_id:
                line.partner_id = line.helpdesk_ticket_id.partner_id or line.partner_id

    def _timesheet_preprocess(self, vals):
        helpdesk_ticket_id = vals.get('helpdesk_ticket_id')
        if helpdesk_ticket_id:
            ticket = self.env['helpdesk.ticket'].browse(helpdesk_ticket_id)
            if ticket.project_id:
                vals['project_id'] = ticket.project_id.id
            vals.update({
                'account_id': ticket.analytic_account_id.id,
            })
        vals = super(AccountAnalyticLine, self)._timesheet_preprocess(vals)
        return vals

    def _timesheet_get_portal_domain(self):
        domain = super(AccountAnalyticLine, self)._timesheet_get_portal_domain()
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            domain = expression.OR([domain, self._timesheet_in_helpdesk_get_portal_domain()])
        return domain

    def _timesheet_in_helpdesk_get_portal_domain(self):
        return [
            '&',
                '&',
                    '&',
                        ('task_id', '=', False),
                        ('helpdesk_ticket_id', '!=', False),
                    '|',
                        ('project_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                        ('helpdesk_ticket_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                ('project_id.privacy_visibility', '=', 'portal')
        ]
