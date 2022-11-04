# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    project_id = fields.Many2one("project.project", string="Project", ondelete="restrict", domain="[('allow_timesheets', '=', True), ('company_id', '=', company_id)]",
        help="Project to which the timesheets of this helpdesk team's tickets will be linked.")
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id')
    total_timesheet_time = fields.Integer(compute="_compute_total_timesheet_time")

    @api.depends('ticket_ids')
    def _compute_total_timesheet_time(self):
        helpdesk_timesheet_teams = self.filtered('use_helpdesk_timesheet')
        if not helpdesk_timesheet_teams:
            self.total_timesheet_time = 0.0
            return
        timesheets_read_group = self.env['account.analytic.line']._read_group(
            [('helpdesk_ticket_id', 'in', helpdesk_timesheet_teams.ticket_ids.filtered(lambda x: not x.stage_id.fold).ids)],
            ['helpdesk_ticket_id', 'unit_amount', 'product_uom_id'],
            ['helpdesk_ticket_id', 'product_uom_id'],
            lazy=False)
        timesheet_data_dict = defaultdict(list)
        uom_ids = set(helpdesk_timesheet_teams.timesheet_encode_uom_id.ids)
        for result in timesheets_read_group:
            uom_id = result['product_uom_id'] and result['product_uom_id'][0]
            if uom_id:
                uom_ids.add(uom_id)
            timesheet_data_dict[result['helpdesk_ticket_id'][0]].append((uom_id, result['unit_amount']))

        uoms_dict = {uom.id: uom for uom in self.env['uom.uom'].browse(uom_ids)}
        for team in helpdesk_timesheet_teams:
            total_time = sum([
                sum([
                    unit_amount * uoms_dict.get(product_uom_id, team.timesheet_encode_uom_id).factor_inv
                    for product_uom_id, unit_amount in timesheet_data
                ], 0.0)
                for ticket_id, timesheet_data in timesheet_data_dict.items()
                if ticket_id in team.ticket_ids.ids
            ], 0.0)
            total_time *= team.timesheet_encode_uom_id.factor
            team.total_timesheet_time = int(round(total_time))
        (self - helpdesk_timesheet_teams).total_timesheet_time = 0

    def _create_project(self, name, allow_billable, other):
        return self.env['project.project'].create({
            'name': name,
            'type_ids': [
                (0, 0, {'name': _('New')}),
            ],
            'allow_timesheets': True,
            **other,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('use_helpdesk_timesheet') and not vals.get('project_id'):
                allow_billable = vals.get('use_helpdesk_sale_timesheet')
                vals['project_id'] = self._create_project(vals['name'], allow_billable, {}).id
        teams = super().create(vals_list)
        teams.sudo()._check_timesheet_group()
        return teams

    def write(self, vals):
        if 'use_helpdesk_timesheet' in vals and not vals['use_helpdesk_timesheet']:
            vals['project_id'] = False
            # to unlink timer when use_helpdesk_timesheet is false
            self.env['timer.timer'].search([
                ('res_model', '=', 'helpdesk.ticket'),
                ('res_id', 'in', self.with_context(active_test=False).ticket_ids.ids)
            ]).unlink()
        result = super(HelpdeskTeam, self).write(vals)
        if 'use_helpdesk_timesheet' in vals:
            self.sudo()._check_timesheet_group()
        for team in self.filtered(lambda team: team.use_helpdesk_timesheet and not team.project_id):
            team.project_id = team._create_project(team.name, team.use_helpdesk_sale_timesheet, {})
        return result

    def _get_timesheet_user_group(self):
        return self.env.ref('hr_timesheet.group_hr_timesheet_user')

    def _check_timesheet_group(self):
        timesheet_teams = self.filtered('use_helpdesk_timesheet')
        use_helpdesk_timesheet_group = self.user_has_groups('helpdesk_timesheet.group_use_helpdesk_timesheet')
        helpdesk_timesheet_group = self.env.ref('helpdesk_timesheet.group_use_helpdesk_timesheet')
        enabled_timesheet_team = lambda: self.env['helpdesk.team'].search([('use_helpdesk_timesheet', '=', True)], limit=1)
        if timesheet_teams and not use_helpdesk_timesheet_group:
            (self._get_helpdesk_user_group() + self._get_timesheet_user_group())\
                .write({'implied_ids': [Command.link(helpdesk_timesheet_group.id)]})
        elif self - timesheet_teams and use_helpdesk_timesheet_group and not enabled_timesheet_team():
            (self._get_helpdesk_user_group() + self._get_timesheet_user_group())\
                .write({'implied_ids': [Command.unlink(helpdesk_timesheet_group.id)]})
            helpdesk_timesheet_group.write({'users': [Command.clear()]})

    def action_view_timesheets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_timesheet.act_hr_timesheet_line_helpdesk")
        action.update({
            'domain': [('helpdesk_ticket_id', 'in', self.ticket_ids.filtered(lambda x: not x.stage_id.fold).ids)],
            'context': {
                'default_project_id': self.project_id.id,
                'graph_groupbys': ['date:week', 'employee_id'],
            },
        })
        return action


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _inherit = ['helpdesk.ticket', 'timer.mixin']

    project_id = fields.Many2one(
        "project.project", related="team_id.project_id", readonly=True, store=True)
    timesheet_ids = fields.One2many('account.analytic.line', 'helpdesk_ticket_id', 'Timesheets',
        help="Time spent on this ticket. By default, your timesheets will be linked to the sales order item of your ticket.\n"
             "Remove the sales order item to make your timesheet entries non billable.")
    use_helpdesk_timesheet = fields.Boolean('Timesheet activated on Team', related='team_id.use_helpdesk_timesheet', readonly=True)
    display_timesheet_timer = fields.Boolean("Display Timesheet Time", compute='_compute_display_timesheet_timer')
    total_hours_spent = fields.Float("Hours Spent", compute='_compute_total_hours_spent', default=0, compute_sudo=True, store=True)
    display_timer_start_secondary = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer = fields.Boolean(compute='_compute_display_timer')
    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days')
    analytic_account_id = fields.Many2one('account.analytic.account',
        compute='_compute_analytic_account_id', store=True, readonly=False,
        string='Analytic Account', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day')

    @api.depends('display_timesheet_timer', 'timer_start', 'timer_pause', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        for ticket in self:
            if not ticket.display_timesheet_timer:
                ticket.update({
                    'display_timer_start_primary': False,
                    'display_timer_start_secondary': False,
                    'display_timer_stop': False,
                    'display_timer_pause': False,
                    'display_timer_resume': False,
                })
            else:
                super(HelpdeskTicket, ticket)._compute_display_timer_buttons()
                ticket.display_timer_start_secondary = ticket.display_timer_start_primary
                if not ticket.timer_start:
                    ticket.update({
                        'display_timer_stop': False,
                        'display_timer_pause': False,
                        'display_timer_resume': False,
                    })
                    if not ticket.total_hours_spent:
                        ticket.display_timer_start_secondary = False
                    else:
                        ticket.display_timer_start_primary = False

    def _compute_display_timer(self):
        if self.env.user.has_group('helpdesk.group_helpdesk_user') and self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            self.display_timer = True
        else:
            self.display_timer = False

    @api.depends('use_helpdesk_timesheet', 'timesheet_ids', 'encode_uom_in_days')
    def _compute_display_timesheet_timer(self):
        for ticket in self:
            ticket.display_timesheet_timer = ticket.use_helpdesk_timesheet and not ticket.encode_uom_in_days

    @api.depends('timesheet_ids')
    def _compute_total_hours_spent(self):
        for ticket in self:
            ticket.total_hours_spent = round(sum(ticket.timesheet_ids.mapped('unit_amount')), 2)

    @api.depends('project_id')
    def _compute_analytic_account_id(self):
        for ticket in self:
            ticket.analytic_account_id = ticket.project_id.analytic_account_id

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the time field labels according to the company timesheet encoding UOM
        makes the view cache dependent on the company timesheet encoding uom"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.company.timesheet_encode_uom_id,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        arch, view = super()._get_view(view_id, view_type, **options)
        arch = self.env['account.analytic.line']._apply_timesheet_label(arch)
        if view_type in ['tree', 'pivot', 'graph', 'cohort'] and self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day'):
            arch = self.env['account.analytic.line']._apply_time_label(arch, related_model=self._name)
        return arch, view

    def action_timer_start(self):
        if not self.user_timer_id.timer_start and self.display_timesheet_timer:
            super().action_timer_start()

    def action_timer_stop(self):
        # timer was either running or paused
        if self.user_timer_id.timer_start and self.display_timesheet_timer:
            minutes_spent = self.user_timer_id._get_minutes_spent()
            minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_min_duration', 0))
            rounding = int(self.env['ir.config_parameter'].sudo().get_param('timesheet_grid.timesheet_rounding', 0))
            minutes_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding)
            return self._action_open_new_timesheet(minutes_spent * 60 / 3600)
        return False

    def _action_open_new_timesheet(self, time_spent):
        return {
            "name": _("Confirm Time Spent"),
            "type": 'ir.actions.act_window',
            "res_model": 'helpdesk.ticket.create.timesheet',
            "views": [[False, "form"]],
            "target": 'new',
            "context": {
                **self.env.context,
                'active_id': self.id,
                'active_model': self._name,
                'default_time_spent': time_spent,
            },
        }
