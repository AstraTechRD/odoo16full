# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY


class HelpdeskSLAReport(models.Model):
    _name = 'helpdesk.sla.report.analysis'
    _description = "SLA Status Analysis"
    _auto = False
    _order = 'create_date DESC'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', readonly=True)
    create_date = fields.Datetime("Ticket Create Date", readonly=True)
    priority = fields.Selection(TICKET_PRIORITY, string='Minimum Priority', readonly=True)
    user_id = fields.Many2one('res.users', string="Assigned To", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Ticket Type", readonly=True)
    ticket_stage_id = fields.Many2one('helpdesk.stage', string="Ticket Stage", readonly=True)
    ticket_deadline = fields.Datetime("Ticket Deadline", readonly=True)
    ticket_closed = fields.Boolean("Ticket Closed", readonly=True)
    ticket_close_hours = fields.Integer("Working Hours to Close", group_operator="avg", readonly=True)
    ticket_assignation_hours = fields.Integer("Working Hours to Assign", group_operator="avg", readonly=True)
    close_date = fields.Datetime("Close date", readonly=True)
    sla_id = fields.Many2one('helpdesk.sla', string='SLA', readonly=True)

    sla_stage_id = fields.Many2one('helpdesk.stage', string="SLA Stage", readonly=True)
    sla_deadline = fields.Datetime("SLA Deadline", group_operator='min', readonly=True)
    sla_reached_datetime = fields.Datetime("SLA Reached Date", group_operator='min', readonly=True)
    sla_status = fields.Selection([('failed', 'SLA Failed'), ('reached', 'SLA Reached'), ('ongoing', 'SLA Ongoing')], string="Status", readonly=True)
    sla_status_fail = fields.Boolean("SLA Status Failed", group_operator='bool_or', readonly=True)
    sla_exceeded_hours = fields.Integer("Working Hours to Reach SLA", group_operator='avg', readonly=True, help="Day to reach the stage of the SLA, without taking the working calendar into account")

    sla_status_successful = fields.Integer("Number of SLA Successful", readonly=True)
    sla_status_failed = fields.Integer("Number of SLA Failed", readonly=True)
    sla_status_ongoing = fields.Integer("Number SLA In Progress", readonly=True)

    successful_sla_rate = fields.Float("% of Successful SLA", group_operator='avg', readonly=True)
    failed_sla_rate = fields.Float("% of Failed SLA", group_operator='avg', readonly=True)
    ongoing_sla_rate = fields.Float("% of SLA In Progress", group_operator='avg', readonly=True)

    team_id = fields.Many2one('helpdesk.team', string='Team', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def _select(self):
        return """
            SELECT DISTINCT T.id as id,
                            T.id AS ticket_id,
                            T.create_date AS create_date,
                            T.team_id,
                            T.stage_id AS ticket_stage_id,
                            T.ticket_type_id,
                            T.user_id,
                            T.partner_id,
                            T.company_id,
                            T.priority AS priority,
                            T.sla_deadline AS ticket_deadline,
                            T.close_hours AS ticket_close_hours,
                            T.assign_hours AS ticket_assignation_hours,
                            T.close_date AS close_date,
                            STAGE.fold AS ticket_closed,
                            SLA.stage_id as sla_stage_id,
                            SLA_S.deadline AS sla_deadline,
                            SLA_S.reached_datetime AS sla_reached_datetime,
                            SLA.id as sla_id,
                            SLA_S.exceeded_hours AS sla_exceeded_hours,
                            SLA_S.reached_datetime >= SLA_S.deadline OR (SLA_S.reached_datetime IS NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC') AS sla_status_fail,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND (SLA_S.deadline IS NULL OR SLA_S.reached_datetime < SLA_S.deadline) THEN 1
                                ELSE 0
                            END AS sla_status_successful,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.reached_datetime >= SLA_S.deadline THEN 1
                                WHEN SLA_S.reached_datetime IS NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC' THEN 1
                                ELSE 0
                            END AS sla_status_failed,
                            CASE
                                WHEN SLA_S.reached_datetime IS NULL AND (SLA_S.deadline IS NULL OR SLA_S.deadline > NOW() AT TIME ZONE 'UTC') THEN 1
                                ELSE 0
                            END AS sla_status_ongoing,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND (SLA_S.deadline IS NULL OR SLA_S.reached_datetime < SLA_S.deadline) THEN 1
                                ELSE 0
                            END AS successful_sla_rate,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.reached_datetime >= SLA_S.deadline THEN 1
                                WHEN SLA_S.reached_datetime IS NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC' THEN 1
                                ELSE 0
                            END AS failed_sla_rate,
                            CASE
                                WHEN SLA_S.reached_datetime IS NULL AND (SLA_S.deadline IS NULL OR SLA_S.deadline > NOW() AT TIME ZONE 'UTC') THEN 1
                                ELSE 0
                            END AS ongoing_sla_rate,
                            CASE
                                WHEN SLA_S.reached_datetime IS NOT NULL AND (SLA_S.deadline IS NULL OR SLA_S.reached_datetime < SLA_S.deadline) THEN 'reached'
                                WHEN (SLA_S.reached_datetime IS NOT NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.reached_datetime >= SLA_S.deadline) OR
                                    (SLA_S.reached_datetime IS NULL AND SLA_S.deadline IS NOT NULL AND SLA_S.deadline < NOW() AT TIME ZONE 'UTC') THEN 'failed'
                                WHEN SLA_S.reached_datetime IS NULL AND (SLA_S.deadline IS NULL OR SLA_S.deadline > NOW() AT TIME ZONE 'UTC') THEN 'ongoing'
                            END AS sla_status
        """

    def _from(self):
        return """
            helpdesk_ticket T
            LEFT JOIN helpdesk_stage STAGE ON T.stage_id = STAGE.id
            RIGHT JOIN helpdesk_sla_status SLA_S ON T.id = SLA_S.ticket_id
            LEFT JOIN helpdesk_sla SLA ON SLA.id = SLA_S.sla_id
        """

    def _where(self):
        return """
            T.active = true
        """

    def _order_by(self):
        return """
            id, sla_stage_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            WHERE %s
            ORDER BY %s
            )""" % (self._table, self._select(), self._from(),
                    self._where(), self._order_by()))
