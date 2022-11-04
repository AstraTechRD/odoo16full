# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY


class HelpdeskTicketReport(models.Model):
    _name = 'helpdesk.ticket.report.analysis'
    _description = "Ticket Analysis"
    _auto = False
    _order = 'create_date DESC'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', readonly=True)
    sla_fail = fields.Boolean(related="ticket_id.sla_fail", readonly=True)
    create_date = fields.Datetime("Created On", readonly=True)
    priority = fields.Selection(TICKET_PRIORITY, string='Minimum Priority', readonly=True)
    user_id = fields.Many2one('res.users', string="Assigned To", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Ticket Type", readonly=True)
    ticket_stage_id = fields.Many2one('helpdesk.stage', string="Ticket Stage", readonly=True)
    ticket_deadline = fields.Datetime("Ticket Deadline", readonly=True)
    ticket_deadline_hours = fields.Float("Hours to SLA Deadline", group_operator="avg", readonly=True)
    ticket_close_hours = fields.Float("Hours to Close", group_operator="avg", readonly=True)
    ticket_open_hours = fields.Float("Hours Open", group_operator="avg", readonly=True)
    ticket_assignation_hours = fields.Float("Hours to Assign", group_operator="avg", readonly=True)
    close_date = fields.Datetime("Close date", readonly=True)
    assign_date = fields.Datetime("First assignment date", readonly=True)
    rating_last_value = fields.Float("Rating (/5)", group_operator="avg", readonly=True)
    active = fields.Boolean("Active", readonly=True)
    team_id = fields.Many2one('helpdesk.team', string='Team', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State', readonly=True)
    first_response_hours = fields.Float("Hours to First Response", group_operator="avg", readonly=True)
    avg_response_hours = fields.Float("Average Hours to Respond", group_operator="avg", readonly=True)

    def _select(self):
        select_str = """
            SELECT T.id AS id,
                   T.id AS ticket_id,
                   T.create_date AS create_date,
                   T.priority AS priority,
                   T.user_id AS user_id,
                   T.partner_id AS partner_id,
                   T.ticket_type_id AS ticket_type_id,
                   T.stage_id AS ticket_stage_id,
                   T.sla_deadline AS ticket_deadline,
                   NULLIF(T.sla_deadline_hours, 0) AS ticket_deadline_hours,
                   NULLIF(T.close_hours, 0) AS ticket_close_hours,
                   EXTRACT(HOUR FROM (COALESCE(T.assign_date, NOW()) - T.create_date)) AS ticket_open_hours,
                   NULLIF(T.assign_hours, 0) AS ticket_assignation_hours,
                   T.close_date AS close_date,
                   T.assign_date AS assign_date,
                   NULLIF(T.rating_last_value, 0) AS rating_last_value,
                   T.active AS active,
                   T.team_id AS team_id,
                   T.company_id AS company_id,
                   T.kanban_state AS kanban_state,
                   NULLIF(T.first_response_hours, 0) AS first_response_hours,
                   NULLIF(T.avg_response_hours, 0) AS avg_response_hours
        """
        return select_str

    def _from(self):
        from_str = """
            helpdesk_ticket T
        """
        return from_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            )""" % (self._table, self._select(), self._from()))
