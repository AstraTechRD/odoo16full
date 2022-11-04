# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime

from dateutil import relativedelta
from collections import defaultdict
from pytz import timezone
from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import float_round
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY
from odoo.addons.rating.models.rating_data import RATING_LIMIT_MIN
from odoo.addons.web.controllers.utils import clean_action


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _inherit = ['mail.alias.mixin', 'mail.thread', 'rating.parent.mixin']
    _description = "Helpdesk Team"
    _order = 'sequence,name'
    _rating_satisfaction_days = 7  # include only last 7 days to compute satisfaction and average

    _sql_constraints = [('not_portal_show_rating_if_not_use_rating',
                         'check (portal_show_rating = FALSE OR use_rating = TRUE)',
                         'It is necessary to enable customer ratings in the settings of your helpdesk team so that they can be displayed on the portal.'), ]

    def _default_stage_ids(self):
        default_stages = self.env['helpdesk.stage']
        for xml_id in ['stage_new', 'stage_in_progress', 'stage_solved', 'stage_cancelled']:
            stage = self.env.ref('helpdesk.%s' % xml_id, raise_if_not_found=False)
            if stage:
                default_stages += stage
        if not default_stages:
            default_stages = self.env['helpdesk.stage'].create({
                'name': _("New"),
                'sequence': 0,
                'template_id': self.env.ref('helpdesk.new_ticket_request_email_template', raise_if_not_found=False).id or None
            })
        return [Command.set(default_stages.ids)]

    def _default_domain_member_ids(self):
        return [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)]

    name = fields.Char('Helpdesk Team', required=True, translate=True)
    description = fields.Html('About Team', translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    sequence = fields.Integer("Sequence", default=10)
    color = fields.Integer('Color Index', default=1)
    ticket_properties = fields.PropertiesDefinition('Ticket Properties')

    stage_ids = fields.Many2many(
        'helpdesk.stage', relation='team_stage_rel', string='Stages',
        default=_default_stage_ids,
        help="Stages the team will use. This team's tickets will only be able to be in these stages.")
    auto_assignment = fields.Boolean("Automatic Assignment")
    assign_method = fields.Selection([
        ('randomly', 'Each user is assigned an equal number of tickets'),
        ('balanced', 'Each user has an equal number of open tickets')],
        string='Assignment Method', default='randomly', required=True,
        help="New tickets will automatically be assigned to the team members that are available, according to their working hours and their time off.")
    member_ids = fields.Many2many('res.users', string='Team Members', domain=lambda self: self._default_domain_member_ids(),
        default=lambda self: self.env.user, required=True)
    privacy_visibility = fields.Selection([
        ('invited_internal', 'Invited internal users'),
        ('internal', 'All internal users'),
        ('portal', 'Invited portal users and all internal users')],
        string='Visibility', required=True,
        default='portal',
        help="People to whom this helpdesk team and its tickets will be visible.\n\n"
            "- Invited internal users: internal users can access the team and the tickets they are following. "
            "This access can be modified on each ticket individually by adding or removing the user as follower.\n"
            "A user with the helpdesk > administrator access right level can still access this team and its tickets, even if they are not explicitely part of the followers.\n\n"
            "- All internal users: all internal users can access the team and all of its tickets without distinction.\n\n"
            "- Invited portal users and all internal users: all internal users can access the team and all of its tickets without distinction.\n"
            "Portal users can only access the tickets they are following. "
            "This access can be modified on each ticket individually by adding or removing the portal user as follower.")
    privacy_visibility_warning = fields.Char('Privacy Visibility Warning', compute='_compute_privacy_visibility_warning')
    access_instruction_message = fields.Char('Access Instruction Message', compute='_compute_access_instruction_message')
    ticket_ids = fields.One2many('helpdesk.ticket', 'team_id', string='Tickets')

    use_alias = fields.Boolean('Email Alias', default=True)
    has_external_mail_server = fields.Boolean(compute='_compute_has_external_mail_server')
    allow_portal_ticket_closing = fields.Boolean('Closure by Customers')
    use_website_helpdesk_form = fields.Boolean('Website Form', compute='_compute_use_website_helpdesk_form', readonly=False, store=True)
    use_website_helpdesk_livechat = fields.Boolean('Live Chat')
    use_website_helpdesk_forum = fields.Boolean('Community Forum')
    use_website_helpdesk_slides = fields.Boolean('Enable eLearning', compute='_compute_use_website_helpdesk_slides', readonly=False, store=True)
    use_website_helpdesk_knowledge = fields.Boolean('Knowledge', compute='_compute_use_website_helpdesk_knowledge', readonly=False, store=True)
    use_helpdesk_timesheet = fields.Boolean(
        'Timesheets', compute='_compute_use_helpdesk_timesheet',
        store=True, readonly=False)
    show_knowledge_base = fields.Boolean(compute='_compute_show_knowledge_base')
    use_helpdesk_sale_timesheet = fields.Boolean(
        'Time Billing', compute='_compute_use_helpdesk_sale_timesheet', store=True,
        readonly=False)
    use_credit_notes = fields.Boolean('Refunds')
    use_coupons = fields.Boolean('Coupons')
    use_fsm = fields.Boolean('Field Service')
    use_product_returns = fields.Boolean('Returns')
    use_product_repairs = fields.Boolean('Repairs')
    use_twitter = fields.Boolean('Twitter')
    use_rating = fields.Boolean('Customer Ratings')
    portal_show_rating = fields.Boolean(
        'Ratings on Website', compute='_compute_portal_show_rating', store=True, readonly=False,
        help="If enabled, portal users will have access to your customer satisfaction statistics from the last 30 days in their portal.\n"
             "They will only have access to the ratings themselves, and not to the written feedback if any was left. You can also manually hide ratings of your choosing.")
    use_sla = fields.Boolean('SLA Policies')
    unassigned_tickets = fields.Integer(string='Unassigned Tickets', compute='_compute_unassigned_tickets')
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Hours',
        default=lambda self: self.env.company.resource_calendar_id, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Working hours used to determine the deadline of SLA Policies.")
    open_ticket_count = fields.Integer("# Open Tickets", compute='_compute_open_ticket_count')
    sla_policy_count = fields.Integer("# SLA Policy", compute='_compute_sla_policy_count')
    ticket_closed = fields.Integer(string='Ticket Closed', compute='_compute_ticket_closed')
    success_rate = fields.Float(string='Success Rate', compute='_compute_success_rate', groups="helpdesk.group_use_sla")
    urgent_ticket = fields.Integer(string='# Urgent Ticket', compute='_compute_urgent_ticket')
    sla_failed = fields.Integer(string='Failed SLA Ticket', compute='_compute_sla_failed')
    # auto close ticket
    auto_close_ticket = fields.Boolean('Automatic Closing')
    auto_close_day = fields.Integer('Inactive Period(days)',
        default=7,
        help="Period of inactivity after which tickets will be automatically closed.")
    from_stage_ids = fields.Many2many('helpdesk.stage', relation='team_stage_auto_close_from_rel',
        string='In Stages',
        domain="[('id', 'in', stage_ids)]")
    to_stage_id = fields.Many2one('helpdesk.stage',
        string='Move to Stage',
        compute="_compute_assign_stage_id", readonly=False, store=True,
        domain="[('id', 'in', stage_ids)]")
    display_alias_name = fields.Char(string='Alias email', compute='_compute_display_alias_name')
    alias_email_from = fields.Char(compute='_compute_alias_email_from')

    @api.constrains('use_website_helpdesk_form', 'privacy_visibility')
    def _check_website_privacy(self):
        if any(t.use_website_helpdesk_form and t.privacy_visibility != 'portal' for t in self):
            raise ValidationError(_('The visibility of the team needs to be set as "Invited portal users and all internal users" in order to use the website form.'))

    @api.depends('auto_close_ticket', 'stage_ids')
    def _compute_assign_stage_id(self):
        stages_dict = {stage['id']: 1 if stage['fold'] else 2 for stage in self.env['helpdesk.stage'].search_read([('id', 'in', self.stage_ids.ids), ('fold', '=', True)], ['id', 'fold'])}
        for team in self:
            if not team.stage_ids:
                team.to_stage_id = False
                continue
            stage_ids = sorted([
                (val, stage_id) for stage_id, val in stages_dict.items() if stage_id in team.stage_ids.ids
            ])
            team.to_stage_id = stage_ids[0][1] if stage_ids else team.stage_ids and team.stage_ids.ids[-1]

    @api.depends('alias_name', 'alias_domain')
    def _compute_display_alias_name(self):
        for team in self:
            alias_name = ''
            if team.alias_name and team.alias_domain:
                alias_name = "%s@%s" % (team.alias_name, team.alias_domain)
            team.display_alias_name = alias_name

    def _compute_alias_email_from(self):
        res = self._notify_get_reply_to()
        for team in self:
            team.alias_email_from = res.get(team.id, False)

    def _compute_has_external_mail_server(self):
        self.has_external_mail_server = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_external_email_server')

    def _compute_unassigned_tickets(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('user_id', '=', False),
            ('team_id', 'in', self.ids),
            ('stage_id.fold', '=', False),
        ], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.unassigned_tickets = mapped_data.get(team.id, 0)

    def _compute_ticket_closed(self):
        dt = datetime.datetime.combine(datetime.date.today() - relativedelta.relativedelta(days=6), datetime.time.min)
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('team_id', 'in', self.ids),
            ('stage_id.fold', '=', True),
            ('close_date', '>=', dt)],
            ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.ticket_closed = mapped_data.get(team.id, 0)

    def _compute_success_rate(self):
        dt = datetime.datetime.combine(datetime.date.today() - relativedelta.relativedelta(days=6), datetime.time.min)
        tickets_read = self.env['helpdesk.ticket'].search_read([
            ('team_id.use_sla', '=', True),
            '|',
            ('stage_id.fold', '=', True),
            ('close_date', '>=', dt)],
            ['team_id', 'sla_deadline', 'sla_reached_late']
        )
        is_failed_tickets_per_team = defaultdict(list)  # key: helpdesk_team_id and value: list of bool (True if ticket is failed)
        today = fields.Datetime.now()
        for res in tickets_read:
            deadline = res.get('sla_deadline', False)
            is_failed_tickets_per_team[res['team_id'][0]].append(
                (deadline and today > deadline) or res.get('sla_reached_late', False)
            )
        for team in self:
            is_failed_tickets = is_failed_tickets_per_team.get(team.id, [])
            success_count = len([ticket for ticket in is_failed_tickets if not ticket])
            total_count = len(is_failed_tickets)
            team.success_rate = float_round(success_count * 100 / total_count, 2) if total_count else 0.0

    def _compute_urgent_ticket(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('team_id', 'in', self.ids),
            ('stage_id.fold', "=", False),
            ('priority', '=', 3)],
            ['team_id'], ['team_id'])
        mapped_data = {data['team_id'][0]: data['team_id_count'] for data in ticket_data}
        for team in self:
            team.urgent_ticket = mapped_data.get(team.id, 0)

    def _compute_sla_failed(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('team_id', 'in', self.ids),
            ('stage_id.fold', '=', False),
            ('sla_fail', '=', True)],
            ['team_id'], ['team_id'])
        mapped_data = {data['team_id'][0]: data['team_id_count'] for data in ticket_data}
        for team in self:
            team.sla_failed = mapped_data.get(team.id, 0)

    def _compute_open_ticket_count(self):
        ticket_data = self.env['helpdesk.ticket'].read_group([
            ('team_id', 'in', self.ids), ('stage_id.fold', '=', False)
        ], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in ticket_data)
        for team in self:
            team.open_ticket_count = mapped_data.get(team.id, 0)

    def _compute_sla_policy_count(self):
        sla_data = self.env['helpdesk.sla'].read_group([('team_id', 'in', self.ids)], ['team_id'], ['team_id'])
        mapped_data = dict((data['team_id'][0], data['team_id_count']) for data in sla_data)
        for team in self:
            team.sla_policy_count = mapped_data.get(team.id, 0)

    @api.depends('use_rating')
    def _compute_portal_show_rating(self):
        without_rating = self.filtered(lambda t: not t.use_rating)
        without_rating.update({'portal_show_rating': False})

    @api.onchange('use_alias', 'name')
    def _onchange_use_alias(self):
        if not self.use_alias:
            self.alias_name = False

    @api.depends('use_website_helpdesk_knowledge', 'use_website_helpdesk_slides')
    def _compute_use_website_helpdesk_form(self):
        teams = self.filtered(lambda team: not team.use_website_helpdesk_form and (team.use_website_helpdesk_knowledge or team.use_website_helpdesk_slides))
        teams.use_website_helpdesk_form = True

    @api.depends('use_website_helpdesk_form')
    def _compute_use_website_helpdesk_slides(self):
        teams = self.filtered(lambda team: not team.use_website_helpdesk_form and team.use_website_helpdesk_slides)
        teams.use_website_helpdesk_slides = False

    @api.depends('use_website_helpdesk_form')
    def _compute_use_website_helpdesk_knowledge(self):
        teams = self.filtered(lambda team: not team.use_website_helpdesk_form and team.use_website_helpdesk_knowledge)
        teams.use_website_helpdesk_knowledge = False

    @api.depends('use_helpdesk_sale_timesheet')
    def _compute_use_helpdesk_timesheet(self):
        sale_timesheet = self.filtered('use_helpdesk_sale_timesheet')
        sale_timesheet.update({'use_helpdesk_timesheet': True})

    @api.depends('use_helpdesk_timesheet')
    def _compute_use_helpdesk_sale_timesheet(self):
        without_timesheet = self.filtered(lambda t: not t.use_helpdesk_timesheet)
        without_timesheet.update({'use_helpdesk_sale_timesheet': False})

    def _compute_show_knowledge_base(self):
        self.show_knowledge_base = False

    @api.depends('privacy_visibility')
    def _compute_privacy_visibility_warning(self):
        for team in self:
            if not team.ids:
                team.privacy_visibility_warning = ''
            elif team.privacy_visibility == 'portal' and team._origin.privacy_visibility != 'portal':
                team.privacy_visibility_warning = _('Customers will be added to the followers of their tickets.')
            elif team.privacy_visibility != 'portal' and team._origin.privacy_visibility == 'portal':
                team.privacy_visibility_warning = _('Portal users will be removed from the followers of the team and its tickets.')
            else:
                team.privacy_visibility_warning = ''

    @api.depends('privacy_visibility')
    def _compute_access_instruction_message(self):
        for team in self:
            if team.privacy_visibility == 'portal':
                team.access_instruction_message = _('Grant portal users access to your helpdesk team or tickets by adding them as followers.')
            elif team.privacy_visibility == 'invited_internal':
                team.access_instruction_message = _('Grant employees access to your helpdesk team or tickets by adding them as followers.')
            else:
                team.access_instruction_message = ''

    def get_knowledge_base_url(self):
        self.ensure_one()
        return self.get_portal_url()

    # ------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------

    def name_get(self):
        res = super().name_get()
        if len(self.env.context.get('allowed_company_ids', [])) <= 1:
            return res
        name_mapping = dict(res)
        team_default_name = _('Customer Care')
        for team in self:
            if team.name == team_default_name:
                name_mapping[team.id] = f'{name_mapping[team.id]} - {team.company_id.name}'
        return list(name_mapping.items())

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(HelpdeskTeam, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        teams.sudo()._check_sla_group()
        teams.sudo()._check_rating_group()
        teams.sudo()._check_modules_to_install()
        if teams.filtered(lambda x: x.auto_close_ticket):
            teams._update_cron()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return teams

    def write(self, vals):
        if vals.get('privacy_visibility'):
            self._change_privacy_visibility(vals['privacy_visibility'])

        result = super(HelpdeskTeam, self).write(vals)
        if 'active' in vals:
            self.with_context(active_test=False).mapped('ticket_ids').write({'active': vals['active']})
        if 'use_sla' in vals:
            self.sudo()._check_sla_group()
        if 'use_rating' in vals:
            self.sudo()._check_rating_group()
        self.sudo()._check_modules_to_install()
        if 'auto_close_ticket' in vals:
            self._update_cron()
        # If you plan to add something after this, use a new environment. The one above is no longer valid after the modules install.
        return result

    def unlink(self):
        stages = self.mapped('stage_ids').filtered(lambda stage: stage.team_ids <= self)  # remove stages that only belong to team in self
        stages.unlink()
        return super(HelpdeskTeam, self).unlink()

    def copy(self, default=None):
        default = dict(default or {})
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        return super().copy(default)

    def _change_privacy_visibility(self, new_visibility):
        """
        Unsubscribe non-internal users from the team and tickets if the team privacy visibility
        goes from 'portal' to a different value.
        If the privacy visibility is set to 'portal', subscribe back tickets partners.
        """
        for team in self:
            if team.privacy_visibility == new_visibility:
                continue
            if new_visibility == 'portal':
                for ticket in team.mapped('ticket_ids').filtered('partner_id'):
                    ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
            elif team.privacy_visibility == 'portal':
                portal_users = team.message_partner_ids.user_ids.filtered('share')
                team.message_unsubscribe(partner_ids=portal_users.partner_id.ids)
                team.mapped('ticket_ids')._unsubscribe_portal_users()

    @api.model
    def _update_cron(self):
        cron = self.env.ref('helpdesk.ir_cron_auto_close_ticket', raise_if_not_found=False)
        cron and cron.toggle(model=self._name, domain=[
            ('auto_close_ticket', '=', True),
            ('auto_close_day', '>', 0),
        ])

    def _get_helpdesk_user_group(self):
        return self.env.ref('helpdesk.group_helpdesk_user')

    def _get_helpdesk_use_sla_group(self):
        return self.env.ref('helpdesk.group_use_sla')

    def _get_helpdesk_use_rating_group(self):
        return self.env.ref('helpdesk.group_use_rating')

    def _check_sla_feature_enabled(self, check_user_has_group=False):
        """ Check if the SLA feature is enabled

            Check if the user can see at least one helpdesk team with `use_sla=True`
            and if the user has the `group_use_sla` group (only done if the `check_user_has_group` parameter is True)

            :param check_user_has_group: If True, then check if the user has the `group_use_sla`
            :return True if the feature is enabled otherwise False.
        """
        user_has_group = self.user_has_groups('helpdesk.group_use_sla') if check_user_has_group else True
        return user_has_group and self.env['helpdesk.team'].search([('use_sla', '=', True)], limit=1)

    def _check_rating_feature_enabled(self, check_user_has_group=False):
        """ Check if the Customer Rating feature is enabled

            Check if the user can see at least one helpdesk team with `use_rating=True`
            and if the user has the `group_use_rating` group (only done if the `check_user_has_group` parameter is True)

            :param check_user_has_group: If True, then check if the user has the `group_use_rating`
            :return True if the feature is enabled otherwise False.
        """
        user_has_group = self.user_has_groups('helpdesk.group_use_rating') if check_user_has_group else True
        return user_has_group and self.env['helpdesk.team'].search([('use_rating', '=', True)], limit=1)

    def _check_sla_group(self):
        sla_teams = self.filtered('use_sla')
        non_sla_teams = self - sla_teams
        use_sla_group = helpdesk_user_group = None
        user_has_use_sla_group = self.user_has_groups('helpdesk.group_use_sla')

        if sla_teams:
            if not user_has_use_sla_group:
                use_sla_group = self._get_helpdesk_use_sla_group()
                helpdesk_user_group = self._get_helpdesk_user_group()
                helpdesk_user_group.write({'implied_ids': [Command.link(use_sla_group.id)]})
            self.env['helpdesk.sla'].with_context(active_test=False).search([
                ('team_id', 'in', sla_teams.ids), ('active', '=', False),
            ]).write({'active': True})

        if non_sla_teams:
            self.env['helpdesk.sla'].search([('team_id', 'in', non_sla_teams.ids)]).write({'active': False})
            if user_has_use_sla_group and not self._check_sla_feature_enabled():
                use_sla_group = use_sla_group or self._get_helpdesk_use_sla_group()
                helpdesk_user_group = helpdesk_user_group or self._get_helpdesk_user_group()
                helpdesk_user_group.write({'implied_ids': [Command.unlink(use_sla_group.id)]})
                use_sla_group.write({'users': [Command.clear()]})

    def _check_rating_group(self):
        rating_teams = self.filtered('use_rating')
        user_has_use_rating_group = self.user_has_groups('helpdesk.group_use_rating')

        if rating_teams and not user_has_use_rating_group:
            self._get_helpdesk_user_group()\
                .write({'implied_ids': [Command.link(self._get_helpdesk_use_rating_group().id)]})
        elif self - rating_teams and user_has_use_rating_group and not self._check_rating_feature_enabled():
            use_rating_group = self._get_helpdesk_use_rating_group()
            self._get_helpdesk_user_group()\
                .write({'implied_ids': [Command.unlink(use_rating_group.id)]})
            use_rating_group.write({'users': [Command.clear()]})

    @api.model
    def _get_field_modules(self):
        # mapping of field names to module names
        return {
            'use_website_helpdesk_form': 'website_helpdesk',
            'use_website_helpdesk_livechat': 'website_helpdesk_livechat',
            'use_website_helpdesk_forum': 'website_helpdesk_forum',
            'use_website_helpdesk_slides': 'website_helpdesk_slides',
            'use_website_helpdesk_knowledge': 'website_helpdesk_knowledge',
            'use_helpdesk_timesheet': 'helpdesk_timesheet',
            'use_helpdesk_sale_timesheet': 'helpdesk_sale_timesheet',
            'use_credit_notes': 'helpdesk_account',
            'use_product_returns': 'helpdesk_stock',
            'use_product_repairs': 'helpdesk_repair',
            'use_coupons': 'helpdesk_sale_loyalty',
            'use_fsm': 'helpdesk_fsm',
        }

    def _check_modules_to_install(self):
        # determine the modules to be installed
        expected = [
            mname
            for fname, mname in self._get_field_modules().items()
            if any(team[fname] for team in self)
        ]
        modules = self.env['ir.module.module']
        if expected:
            STATES = ('installed', 'to install', 'to upgrade')
            modules = modules.search([('name', 'in', expected)])
            modules = modules.filtered(lambda module: module.state not in STATES)

        if modules:
            modules.button_immediate_install()

        # just in case we want to do something if we install a module. (like a refresh ...)
        return bool(modules)

    # ------------------------------------------------------------
    # Mail Alias Mixin
    # ------------------------------------------------------------

    def _alias_get_creation_values(self):
        values = super(HelpdeskTeam, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('helpdesk.ticket').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['team_id'] = self.id
            if not self.alias_name:
                values['alias_name'] = self.name.replace(' ', '-')
        return values

    # ------------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------------

    @api.model
    def retrieve_dashboard(self):
        domain = [('user_id', '=', self.env.uid)]
        group_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        list_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        user_uses_sla = self._check_sla_feature_enabled(check_user_has_group=True)

        if user_uses_sla:
            group_fields.insert(1, 'sla_deadline:year')
            group_fields.insert(2, 'sla_deadline:hour')
            group_fields.insert(3, 'sla_reached_late')
            list_fields.insert(1, 'sla_deadline')
            list_fields.insert(2, 'sla_reached_late')

        HelpdeskTicket = self.env['helpdesk.ticket']
        show_demo = not bool(HelpdeskTicket.search([], limit=1))
        result = {
            'helpdesk_target_closed': self.env.user.helpdesk_target_closed,
            'helpdesk_target_rating': self.env.user.helpdesk_target_rating,
            'helpdesk_target_success': self.env.user.helpdesk_target_success,
            'today': {'count': 0, 'rating': 0, 'success': 0},
            '7days': {'count': 0, 'rating': 0, 'success': 0},
            'my_all': {'count': 0, 'hours': 0, 'failed': 0},
            'my_high': {'count': 0, 'hours': 0, 'failed': 0},
            'my_urgent': {'count': 0, 'hours': 0, 'failed': 0},
            'show_demo': show_demo,
            'rating_enable': False,
            'success_rate_enable': user_uses_sla
        }

        if show_demo:
            result.update({
                'my_all': {'count': 10, 'hours': 30, 'failed': 4},
                'my_high': {'count': 3, 'hours': 10, 'failed': 2},
                'my_urgent': {'count': 2, 'hours': 15, 'failed': 1},
                'today': {'count': 1, 'rating': 50, 'success': 50},
                '7days': {'count': 15, 'rating': 70, 'success': 80},
                'helpdesk_target_rating': 80,
                'helpdesk_target_success': 85,
                'helpdesk_target_closed': 85,
            })
            return result

        def _is_sla_failed(data):
            deadline = data.get('sla_deadline')
            sla_deadline = fields.Datetime.now() > deadline if deadline else False
            return sla_deadline or data.get('sla_reached_late')

        def add_to(ticket, key="my_all"):
            result[key]['count'] += 1
            result[key]['hours'] += ticket['open_hours']
            if _is_sla_failed(ticket):
                result[key]['failed'] += 1

        tickets = HelpdeskTicket.search_read(
            expression.AND([
                domain,
                [('stage_id.fold', '=', False)]
            ]),
            ['sla_deadline', 'open_hours', 'sla_reached_late', 'priority']
        )
        for ticket in tickets:
            add_to(ticket, 'my_all')
            if ticket['priority'] == '2':
                add_to(ticket, 'my_high')
            if ticket['priority'] == '3':
                add_to(ticket, 'my_urgent')

        dt = fields.Date.context_today(self)
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.fold', '=', True), ('close_date', '>=', dt)], list_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['today']['count'] += ticket['__count']
            if not _is_sla_failed(ticket):
                result['today']['success'] += ticket['__count']

        dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.fold', '=', True), ('close_date', '>=', dt)], list_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['7days']['count'] += ticket['__count']
            if not _is_sla_failed(ticket):
                result['7days']['success'] += ticket['__count']

        result['today']['success'] = fields.Float.round(result['today']['success'] * 100 / (result['today']['count'] or 1), 2)
        result['7days']['success'] = fields.Float.round(result['7days']['success'] * 100 / (result['7days']['count'] or 1), 2)
        result['my_all']['hours'] = fields.Float.round(result['my_all']['hours'] / (result['my_all']['count'] or 1), 2)
        result['my_high']['hours'] = fields.Float.round(result['my_high']['hours'] / (result['my_high']['count'] or 1), 2)
        result['my_urgent']['hours'] = fields.Float.round(result['my_urgent']['hours'] / (result['my_urgent']['count'] or 1), 2)

        if self._check_rating_feature_enabled(check_user_has_group=True):
            result['rating_enable'] = True
            # rating of today
            domain = [('user_id', '=', self.env.uid)]
            today = fields.Date.today()
            one_week_before = today - relativedelta.relativedelta(weeks=1)
            helpdesk_ratings = self.env['rating.rating'].search([
                ('res_model', '=', 'helpdesk.ticket'),
                ('res_id', '!=', False),
                ('write_date', '>', fields.Datetime.to_string(one_week_before)),
                ('write_date', '<=', today),
                ('rating', '>=', RATING_LIMIT_MIN),
                ('consumed', '=', True),
            ])
            tickets = HelpdeskTicket.search([('id', 'in', helpdesk_ratings.mapped('res_id')), ('user_id', '=', self._uid)])
            today_rating_stat = {'count': 0.0, 'score': 0.0}
            rating_stat = {**today_rating_stat}
            for rating in helpdesk_ratings:
                if rating.res_id not in tickets.ids:
                    continue
                if rating.write_date.date() == today:
                    today_rating_stat['count'] += 1
                    today_rating_stat['score'] += rating.rating
                rating_stat['score'] += rating.rating
                rating_stat['count'] += 1

            avg = lambda d: fields.Float.round(d['score'] / d['count'] if d['count'] > 0 else 0.0, 2) * 20

            result['today']['rating'] = avg(today_rating_stat)
            result['7days']['rating'] = avg(rating_stat)
        return result

    def _action_view_rating(self, period=False, only_closed_tickets=False, user_id=None):
        """ return the action to see the rating about the tickets of the Team on the period wished.
            :param period: either 'seven_days' or 'today' is defined to add a default filter for the ratings.
            :param only_my_closed: True will include only the tickets in a closed stage.
            :param user_id: id of the user to get the ratings only in the tickets belongs to the user.
        """
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.rating_rating_action_helpdesk")
        action = clean_action(action, self.env)
        domain = [('team_id', 'in', self.ids)]
        context = dict(ast.literal_eval(action.get('context', {})), search_default_my_ratings=True)
        update_views = {}
        if period == 'seven_days':
            domain += [('close_date', '>=', fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6))))]
            update_views[self.env.ref("helpdesk.rating_rating_view_seven_days_pivot_inherit_helpdesk").id] = 'pivot'
            update_views[self.env.ref('helpdesk.rating_rating_view_seven_days_graph_inherit_helpdesk').id] = 'graph'
            context['search_default_last_7days'] = True
        elif period == 'today':
            context['search_default_today'] = True
            if '__count__' in context.get('pivot_measures', {}):
                context.get('pivot_measures').remove('__count__')
            domain += [('close_date', '>=', fields.Datetime.to_string(datetime.date.today()))]
            update_views[self.env.ref("helpdesk.rating_rating_view_today_pivot_inherit_helpdesk").id] = 'pivot'
            update_views[self.env.ref('helpdesk.rating_rating_view_today_graph_inherit_helpdesk').id] = 'graph'
        action['views'] = [(state, view) for state, view in action['views'] if view not in update_views.values()] + list(update_views.items())
        if only_closed_tickets:
            domain += [('stage_id.fold', '=', True)]
        if user_id:
            domain += [('user_id', '=', user_id)]

        ticket_ids = self.env['helpdesk.ticket'].search(domain).ids
        action.update({
            'context': context,
            'domain': [('res_id', 'in', ticket_ids), ('rating', '>=', RATING_LIMIT_MIN), ('res_model', '=', 'helpdesk.ticket'), ('consumed', '=', True)],
        })
        return action

    def action_view_ticket(self):
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_team")
        action['display_name'] = self.name
        return action

    def _get_action_view_ticket_params(self, is_ticket_closed=False):
        """ Get common params for the actions

            :param is_ticket_closed: Boolean if True, then we want to see the tickets closed in last 7 days
            :returns dict containing the params to update into the action.
        """
        is_ticket_closed_domain_operator = '|' if is_ticket_closed else '&'
        domain = [
            is_ticket_closed_domain_operator,
            ('stage_id.fold', '=', is_ticket_closed),
            ('team_id', 'in', self.ids),
        ]
        context = {
            'search_default_is_open': not is_ticket_closed,
            'default_team_id': self.id,
        }
        view_mode = 'tree,kanban,activity'
        if is_ticket_closed:
            domain = expression.AND([domain, [
                ('close_date', '>=', datetime.date.today() - datetime.timedelta(days=6)),
            ]])
            context.update(search_default_closed_last_7days=True)
        return {
            'domain': domain,
            'context': context,
            'view_mode': view_mode,
        }

    def action_view_closed_ticket(self):
        action = self.action_view_ticket()
        action.update(self._get_action_view_ticket_params(True))
        return action

    def action_view_success_rate(self):
        action = self.action_view_ticket()
        action_params = self._get_action_view_ticket_params(True)
        action.update(
            domain=expression.AND([
                action_params['domain'],
                [('sla_fail', "!=", True), ('team_id', 'in', self.ids)],
            ]),
            context={
                **action_params['context'],
                'search_default_sla_success': True,
            },
            view_mode=action_params['view_mode'],
            views=[(False, view) for view in action_params['view_mode'].split(",")],
        )
        return action

    def action_view_customer_satisfaction(self):
        action = self._action_view_rating(period='seven_days')
        action['context'] = {**self.env.context, **action['context'], 'search_default_my_ratings': True}
        return action

    def action_view_open_ticket(self):
        action = self.action_view_ticket()
        action_params = self._get_action_view_ticket_params()
        action.update({
            'context': action_params['context'],
            'domain': action_params['domain'],
        })
        return action

    def action_view_urgent(self):
        action = self.action_view_ticket()
        action_params = self._get_action_view_ticket_params()
        action.update({
            'context': action_params['context'],
            'domain': expression.AND([action_params['domain'], [('priority', '=', 3)]]),
        })
        return action

    def action_view_sla_failed(self):
        action = self.action_view_ticket()
        action_params = self._get_action_view_ticket_params()
        action.update({
            'context': {
                **action_params['context'],
                'search_default_sla_failed': True,
            },
            'domain': expression.AND([action_params['domain'], [('sla_fail', '=', True)]]),
        })
        return action

    def action_view_rating_today(self):
        #  call this method of on click "Customer Rating" button on dashbord for today rating of teams tickets
        return self.search([('member_ids', 'in', self._uid)])._action_view_rating(period='today', user_id=self._uid)

    def action_view_rating_7days(self):
        #  call this method of on click "Customer Rating" button on dashbord for last 7days rating of teams tickets
        return self.search([('member_ids', 'in', self._uid)])._action_view_rating(period='seven_days', user_id=self._uid)

    def action_view_all_rating(self):
        """ return the action to see all the rating about the all sort of activity of the team (tickets) """
        return self._action_view_rating()

    def action_view_team_rating(self):
        self.ensure_one()
        action = self._action_view_rating()
        # Before this changes if some tickets are archived in the helpdesk team, we count the ratings of them + the active tickets.
        # Do we really want to count the ratings of the archived tickets?
        ratings = self.env['rating.rating'].search(action['domain'])
        if len(ratings) == 1:
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_id': ratings.id
            })
        else:
            action['context'] = {'search_default_rating_last_30_days': 1}
        return action

    def action_view_open_ticket_view(self):
        action = self.action_view_ticket()
        action.update({
            'display_name': _("Tickets"),
            'domain': [('team_id', '=', self.id), ('stage_id.fold', '=', False)],
        })
        return action

    def action_view_sla_policy(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_sla_action")
        if self.sla_policy_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.env['helpdesk.sla'].search([('team_id', '=', self.id)], limit=1).id,
                'views': [(False, 'form')],
            })
        action.update({
            'context': {'default_team_id': self.id},
            'domain': [('team_id', '=', self.id)],
        })
        return action

    @api.model
    def _get_working_user_interval(self, start_dt, end_dt, calendar, users, compute_leaves=True):
        # This method is intended to be overridden in hr_holidays in order to take non-validated leaves into account
        return calendar._work_intervals_batch(
            start_dt,
            end_dt,
            resources=users.resource_ids,
            compute_leaves=compute_leaves
        )

    def _get_working_users_per_first_working_day(self):
        tz = timezone(self._context.get('tz') or 'UTC')
        start_dt = fields.Datetime.now().astimezone(tz)
        end_dt = start_dt + relativedelta.relativedelta(days=7, hour=23, minute=59, second=59)
        workers_per_first_working_date = defaultdict(list)
        members_per_calendar = defaultdict(lambda: self.env['res.users'])
        company_calendar = self.env.company.resource_calendar_id
        for member in self.member_ids:
            calendar = member.resource_calendar_id or company_calendar
            members_per_calendar[calendar] |= member
        for calendar, users in members_per_calendar.items():
            work_intervals_per_resource = self._get_working_user_interval(start_dt, end_dt, calendar, users)
            for user in users:
                for resource_id in user.resource_ids.ids:
                    intervals = work_intervals_per_resource[resource_id]
                    if intervals:
                        # select the start_date of the first interval to get the first working day for this user
                        workers_per_first_working_date[(intervals._items)[0][0].date()].append(user.id)
                        break
                # if the user doesn't linked to any employee then add according to company calendar
                if user.id and not user.resource_ids:
                    intervals = work_intervals_per_resource[False]
                    if intervals:
                        workers_per_first_working_date[(intervals._items)[0][0].date()].append(user.id)
        return [value for key, value in sorted(workers_per_first_working_date.items())]

    def _determine_user_to_assign(self):
        """ Get a dict with the user (per team) that should be assign to the nearly created ticket according to the team policy
            :returns a mapping of team identifier with the "to assign" user (maybe an empty record).
            :rtype : dict (key=team_id, value=record of res.users)
        """
        team_without_manually = self.filtered(lambda x: x.assign_method in ['randomly', 'balanced'] and x.auto_assignment)
        users_per_working_days = team_without_manually._get_working_users_per_first_working_day()
        result = dict.fromkeys(self.ids, self.env['res.users'])
        for team in team_without_manually:
            member_ids = team.member_ids.ids  # By default, all members of the team
            for user_ids in users_per_working_days:
                if any(user_id in team.member_ids.ids for user_id in user_ids):
                    # filter members in team to get the ones working in the nearest date of today.
                    member_ids = [user_id for user_id in user_ids if user_id in self.member_ids.ids]
                    break

            if team.assign_method == 'randomly':  # randomly means new tickets get uniformly distributed
                last_assigned_user = self.env['helpdesk.ticket'].search([('team_id', '=', team.id)], order='create_date desc, id desc', limit=1).user_id
                index = 0
                if last_assigned_user and last_assigned_user.id in member_ids:
                    previous_index = member_ids.index(last_assigned_user.id)
                    index = (previous_index + 1) % len(member_ids)
                result[team.id] = self.env['res.users'].browse(member_ids[index])
            elif team.assign_method == 'balanced':  # find the member with the least open ticket
                ticket_count_data = self.env['helpdesk.ticket'].read_group([('stage_id.fold', '=', False), ('user_id', 'in', member_ids), ('team_id', '=', team.id)], ['user_id'], ['user_id'])
                open_ticket_per_user_map = dict.fromkeys(member_ids, 0)  # dict: user_id -> open ticket count
                open_ticket_per_user_map.update((item['user_id'][0], item['user_id_count']) for item in ticket_count_data)
                result[team.id] = self.env['res.users'].browse(min(open_ticket_per_user_map, key=open_ticket_per_user_map.get))
        return result

    def _determine_stage(self):
        """ Get a dict with the stage (per team) that should be set as first to a created ticket
            :returns a mapping of team identifier with the stage (maybe an empty record).
            :rtype : dict (key=team_id, value=record of helpdesk.stage)
        """
        result = dict.fromkeys(self.ids, self.env['helpdesk.stage'])
        for team in self:
            result[team.id] = self.env['helpdesk.stage'].search([('team_ids', 'in', team.id)], order='sequence', limit=1)
        return result

    def _get_closing_stage(self):
        """
            Return the first closing kanban stage or the last stage of the pipe if none
        """
        closed_stage = self.stage_ids.filtered(lambda stage: stage.fold)
        if not closed_stage:
            closed_stage = self.stage_ids[-1]
        return closed_stage

    def _cron_auto_close_tickets(self):
        teams = self.env['helpdesk.team'].search_read(
            domain=[
                ('auto_close_ticket', '=', True),
                ('auto_close_day', '>', 0),
                ('to_stage_id', '!=', False)],
            fields=[
                'id',
                'auto_close_day',
                'from_stage_ids',
                'to_stage_id']
        )
        teams_dict = defaultdict(dict)  # key: team_id, values: the remaining result of the search_group
        today = fields.datetime.today()
        for team in teams:
            # Compute the threshold_date
            team['threshold_date'] = today - relativedelta.relativedelta(days=team['auto_close_day'])
            teams_dict[team['id']] = team
        tickets_domain = [('stage_id.fold', '=', False), ('team_id', 'in', list(teams_dict.keys()))]
        tickets = self.env['helpdesk.ticket'].search(tickets_domain)

        def is_inactive_ticket(ticket):
            team = teams_dict[ticket.team_id.id]
            is_write_date_ok = ticket.write_date <= team['threshold_date']
            if team['from_stage_ids']:
                is_stage_ok = ticket.stage_id.id in team['from_stage_ids']
            else:
                is_stage_ok = not ticket.stage_id.fold
            return is_write_date_ok and is_stage_ok

        inactive_tickets = tickets.filtered(is_inactive_ticket)
        for ticket in inactive_tickets:
            # to_stage_id is mandatory in the view but not in the model so it is better to test it.
            if teams_dict[ticket.team_id.id]['to_stage_id']:
                ticket.write({'stage_id': teams_dict[ticket.team_id.id]['to_stage_id'][0]})

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if len(self) == 1:
            optional_subtypes = [('use_credit_notes', self.env.ref('helpdesk.mt_team_ticket_refund_posted')),
                                 ('use_credit_notes', self.env.ref('helpdesk.mt_team_ticket_refund_cancel')),
                                 ('use_product_returns', self.env.ref('helpdesk.mt_team_ticket_return_done')),
                                 ('use_product_returns', self.env.ref('helpdesk.mt_team_ticket_return_cancel')),
                                 ('use_product_repairs', self.env.ref('helpdesk.mt_team_ticket_repair_done')),
                                 ('use_product_repairs', self.env.ref('helpdesk.mt_team_ticket_repair_cancel')),]
            for field, subtype in optional_subtypes:
                if not self[field] and subtype in res:
                    res -= subtype
        return res

class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _description = 'Helpdesk Stage'
    _order = 'sequence, id'

    def _default_team_ids(self):
        team_id = self.env.context.get('default_team_id')
        if team_id:
            return [(4, team_id, 0)]

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer('Sequence', default=10)
    fold = fields.Boolean(
        'Folded in Kanban',
        help='Tickets in a folded stage are considered as closed.')
    team_ids = fields.Many2many(
        'helpdesk.team', relation='team_stage_rel', string='Teams',
        default=_default_team_ids)
    template_id = fields.Many2one(
        'mail.template', 'Email Template',
        domain="[('model', '=', 'helpdesk.ticket')]",
        help="Email automatically sent to the customer when the ticket reaches this stage.\n"
             "By default, the email will be sent from the email alias of the helpdesk team.\n"
             "Otherwise it will be sent from the company's email address, or from the catchall (as defined in the System Parameters).")
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True)
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready'), translate=True, required=True)
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        res = self.env['helpdesk.ticket'].read_group(
            [('stage_id', 'in', self.ids)],
            ['stage_id'], ['stage_id'])
        stage_data = {r['stage_id'][0]: r['stage_id_count'] for r in res}
        for stage in self:
            stage.ticket_count = stage_data.get(stage.id, 0)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['helpdesk.ticket'].search([('stage_id', 'in', self.ids)]).write({'active': False})
        return super(HelpdeskStage, self).write(vals)

    def toggle_active(self):
        res = super().toggle_active()
        stage_active = self.filtered('active')
        if stage_active and sum(stage_active.with_context(active_test=False).mapped('ticket_count')) > 0:
            wizard = self.env['helpdesk.stage.delete.wizard'].create({
                'stage_ids': stage_active.ids,
            })

            return {
                'name': _('Unarchive Tickets'),
                'view_mode': 'form',
                'res_model': 'helpdesk.stage.delete.wizard',
                'views': [(self.env.ref('helpdesk.view_helpdesk_stage_unarchive_wizard').id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': wizard.id,
                'target': 'new',
            }
        return res

    def action_unlink_wizard(self, stage_view=False):
        self = self.with_context(active_test=False)
        # retrieves all the teams with a least 1 ticket in that stage
        # a ticket can be in a stage even if the team is not assigned to the stage
        readgroup = self.with_context(active_test=False).env['helpdesk.ticket'].read_group(
            [('stage_id', 'in', self.ids), ('team_id', '!=', False)],
            ['team_id'],
            ['team_id'])
        team_ids = list(set([team['team_id'][0] for team in readgroup] + self.team_ids.ids))

        wizard = self.env['helpdesk.stage.delete.wizard'].create({
            'team_ids': team_ids,
            'stage_ids': self.ids
        })

        context = dict(self.env.context)
        context['stage_view'] = stage_view
        return {
            'name': _('Delete Stage'),
            'view_mode': 'form',
            'res_model': 'helpdesk.stage.delete.wizard',
            'views': [(self.env.ref('helpdesk.view_helpdesk_stage_delete_wizard').id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wizard.id,
            'target': 'new',
            'context': context,
        }

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('stage_id', 'in', self.ids)],
            'context': {
                'default_stage_id': self.id,
            },
        })
        return action


class HelpdeskSLA(models.Model):
    _name = "helpdesk.sla"
    _order = "name"
    _description = "Helpdesk SLA Policies"

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'team_id' in fields_list or 'stage_id' in fields_list:
            team = self.env['helpdesk.team'].search([], limit=1)
            defaults['team_id'] = team.id
            stages = team.stage_ids.filtered(lambda x: x.fold)
            defaults['stage_id'] = stages and stages.ids[0] or team.stage_ids and team.stage_ids.ids[-1]
        return defaults

    name = fields.Char(required=True, index=True, translate=True)
    description = fields.Html('SLA Policy Description', translate=True)
    active = fields.Boolean('Active', default=True)
    team_id = fields.Many2one('helpdesk.team', 'Team', required=True)
    ticket_type_ids = fields.Many2many(
        'helpdesk.ticket.type', string='Types')
    tag_ids = fields.Many2many(
        'helpdesk.tag', string='Tags')
    stage_id = fields.Many2one(
        'helpdesk.stage', 'Target Stage',
        help='Minimum stage a ticket needs to reach in order to satisfy this SLA.')
    exclude_stage_ids = fields.Many2many(
        'helpdesk.stage', string='Excluding Stages', copy=True,
        domain="[('id', '!=', stage_id.id)]",
        help="The time spent in these stages won't be taken into account in the calculation of the SLA.")
    priority = fields.Selection(
        TICKET_PRIORITY, string='Priority',
        default='1', required=True)
    partner_ids = fields.Many2many(
        'res.partner', string="Customers")
    company_id = fields.Many2one('res.company', 'Company', related='team_id.company_id', readonly=True, store=True)
    time = fields.Float('In', default=0, required=True,
        help='Maximum number of working hours a ticket should take to reach the target stage, starting from the date it was created.')
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        res = self.env['helpdesk.ticket'].read_group(
            [('sla_ids', 'in', self.ids), ('stage_id.fold', '=', False)],
            ['sla_ids'], ['sla_ids'])
        sla_data = {r['sla_ids']: r['sla_ids_count'] for r in res}
        for sla in self:
            sla.ticket_count = sla_data.get(sla.id, 0)

    def copy(self, default=None):
        default = dict(default or {})
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        return super().copy(default)

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('sla_ids', 'in', self.ids)],
            'context': {
                'search_default_is_open': True,
                'create': False,
            },
        })
        return action
