# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import uuid
from werkzeug.urls import url_encode, url_join

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

SHORT_CODE_PATTERN = re.compile(r"^[\w-]+$")


class AppointmentShare(models.Model):
    _name = 'appointment.invite'
    _description = 'Appointment Invite'
    _order = 'create_date DESC, id DESC'
    _rec_name = 'short_code'

    access_token = fields.Char('Token', default=lambda s: uuid.uuid4(), required=True, copy=False, readonly=True)
    short_code = fields.Char('Short Code', default=lambda s: s._get_unique_short_code(), required=True)
    short_code_format_warning = fields.Boolean('Short Code Format Warning', compute="_compute_short_code_warning")
    short_code_unique_warning = fields.Boolean('Short Code Unique Warning', compute="_compute_short_code_warning")
    base_book_url = fields.Char('Base Link URL', compute="_compute_base_book_url")
    book_url = fields.Char('Link URL', compute='_compute_book_url')
    redirect_url = fields.Char('Redirect URL', compute='_compute_redirect_url')

    appointment_type_ids = fields.Many2many('appointment.type', string='Appointment Types', domain="[('category', '=', 'website')]")
    appointment_type_info_msg = fields.Html('No User Assigned Message', compute='_compute_appointment_type_info_msg')
    appointment_type_count = fields.Integer('Selected Appointments Count', compute='_compute_appointment_type_count', store=True)
    suggested_staff_user_ids = fields.Many2many(
        'res.users', related='appointment_type_ids.staff_user_ids', string='Possible users',
        help="Get the users linked to the appointment type selected to apply a domain on the users that can be selected")
    suggested_staff_user_count = fields.Integer('# Staff Users', compute='_compute_suggested_staff_user_count')
    staff_users_choice = fields.Selection(
        selection=[
            ('current_user', 'Me'),
            ('all_assigned_users', 'Any User'),
            ('specific_users', 'Specific Users')],
        string='Assign to', compute='_compute_staff_users_choice', store=True, readonly=False)
    staff_user_ids = fields.Many2many('res.users', string='Users', domain="[('id','in',suggested_staff_user_ids)]",
        compute='_compute_staff_user_ids', store=True, readonly=False)

    calendar_event_ids = fields.One2many('calendar.event', 'appointment_invite_id', string="Booked Appointments", readonly=True)

    _sql_constraints = [
        ('short_code_uniq', 'UNIQUE (short_code)', 'The URL is already taken, please pick another code.')
    ]

    @api.constrains('short_code')
    def _check_short_code_format(self):
        invalid_invite = next((invite for invite in self if invite.short_code_format_warning), False)
        if invalid_invite:
            raise ValidationError(_(
                "Only letters, numbers, underscores and dashes are allowed in your links. You need to adapt %s.", invalid_invite.short_code
            ))

    @api.depends('appointment_type_ids', 'appointment_type_count')
    def _compute_appointment_type_info_msg(self):
        '''
            When there is more than one appointment type selected to be shared and at least one doesn't have any staff user assigned,
            display an alert info to tell the current user that, without staff users, an appointment type won't be published.
        '''
        for invite in self:
            appt_without_staff_user = invite.appointment_type_ids.filtered_domain([('staff_user_ids', '=', False)])
            if appt_without_staff_user and invite.appointment_type_count > 1:
                invite.appointment_type_info_msg = _(
                    'The following appointment type(s) have no staff assigned: %s.',
                    ', '.join(appt_without_staff_user.mapped('name'))
                )
            else:
                invite.appointment_type_info_msg = False

    @api.depends('appointment_type_ids')
    def _compute_appointment_type_count(self):
        appointment_data = self.env['appointment.type'].read_group(
            [('appointment_invite_ids', 'in', self.ids)],
            ['appointment_invite_ids'],
            'appointment_invite_ids',
        )
        mapped_data = {m['appointment_invite_ids'][0]: m['appointment_invite_ids_count'] for m in appointment_data}
        for invite in self:
            if isinstance(invite.id, models.NewId):
                invite.appointment_type_count = len(invite.appointment_type_ids)
            else:
                invite.appointment_type_count = mapped_data.get(invite.id, 0)

    @api.depends('short_code')
    def _compute_base_book_url(self):
        for invite in self:
            invite.base_book_url = url_join(invite.get_base_url(), '/book/')

    @api.depends('short_code')
    def _compute_short_code_warning(self):
        for invite in self:
            invite.short_code_format_warning = not bool(re.match(SHORT_CODE_PATTERN, invite.short_code)) if invite.short_code else False
            invite.short_code_unique_warning = bool(self.env['appointment.invite'].search_count([
                ('id', '!=', invite._origin.id), ('short_code', '=', invite.short_code)]))

    @api.depends('appointment_type_ids')
    def _compute_staff_users_choice(self):
        for invite in self:
            if len(invite.appointment_type_ids) != 1:
                invite.staff_users_choice = False
            elif self.env.user in invite.appointment_type_ids._origin.staff_user_ids:
                invite.staff_users_choice = 'current_user'
            else:
                invite.staff_users_choice = 'all_assigned_users'

    @api.depends('appointment_type_ids', 'staff_users_choice')
    def _compute_staff_user_ids(self):
        for invite in self:
            if invite.staff_users_choice == "current_user" and \
                    self.env.user.id in invite.appointment_type_ids.staff_user_ids.ids:
                invite.staff_user_ids = self.env.user
            else:
                invite.staff_user_ids = False

    @api.depends('suggested_staff_user_ids')
    def _compute_suggested_staff_user_count(self):
        for invite in self:
            invite.suggested_staff_user_count = len(invite.suggested_staff_user_ids)

    @api.depends('base_book_url', 'short_code')
    def _compute_book_url(self):
        """
        Compute a short link linked to an appointment invitation.
        """
        for invite in self:
            invite.book_url = url_join(invite.base_book_url, invite.short_code) if invite.short_code else False

    @api.depends('appointment_type_ids', 'staff_user_ids')
    def _compute_redirect_url(self):
        """
        Compute a link that will be share for the user depending on the appointment types and users
        selected. We allow to preselect a group of them if there is only one appointment type selected.
        Indeed, it would be too complex to manage ones with multiple appointment types.
        Two possible params can be generated with the link:
            - filter_staff_user_ids: which allows the user to select an user between the ones selected
            - filter_appointment_type_ids: which display a selection of appointment types to user from which
            they can choose
        """
        for invite in self:
            if len(invite.appointment_type_ids) == 1:
                base_redirect_url = url_join("/appointment/", str(invite.appointment_type_ids.id))
            else:
                base_redirect_url = '/appointment'

            invite.redirect_url = '%s?%s' % (
                base_redirect_url,
                url_encode(invite._get_redirect_url_parameters()),
            )

    def _get_redirect_url_parameters(self):
        self.ensure_one()
        url_param = {
            'invite_token': self.access_token,
        }
        if self.appointment_type_ids:
            url_param.update({
                'filter_appointment_type_ids': str(self.appointment_type_ids.ids),
            })
        if self.staff_user_ids:
            url_param.update({
                'filter_staff_user_ids': str(self.staff_user_ids.ids)
            })
        return url_param

    def _check_appointments_params(self, appointment_types, users):
        """
        Check if the param receive through the URL match with the appointment invite info
        :param recordset appointment_types: the appointment types representing the filter_appointment_type_ids
        :param recordset users: the staff users representing the filter_staff_user_ids
        """
        self.ensure_one()
        if self.appointment_type_ids != appointment_types or self.staff_user_ids != users:
            return False
        return True

    def _get_unique_short_code(self, short_code=False):
        short_access_token = self.access_token[:8] if self.access_token else uuid.uuid4().hex[:8]
        short_code = short_code or self.short_code or short_access_token
        nb_short_code = self.env['appointment.invite'].search_count([('id', '!=', self._origin.id), ('short_code', '=', short_code)])
        if bool(nb_short_code):
            short_code = "%s_%s" % (short_code, nb_short_code)
        return short_code

    @api.autovacuum
    def _gc_appointment_invite(self):
        limit_dt = fields.Datetime.subtract(fields.Datetime.now(), months=3)

        invites = self.env['appointment.invite'].search([('create_date', '<=', limit_dt)])

        to_remove = invites.filtered(lambda invite: not invite.calendar_event_ids or invite.calendar_event_ids[-1].end < limit_dt)
        to_remove.unlink()
