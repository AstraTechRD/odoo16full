# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar as cal
import random
import pytz
from datetime import datetime, timedelta, time
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from babel.dates import format_datetime, format_time
from werkzeug.urls import url_encode, url_join

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.addons.base.models.res_partner import _tz_get


class AppointmentType(models.Model):
    _name = "appointment.type"
    _description = "Appointment Type"
    _inherit = ['mail.thread']
    _order = "sequence, id"

    @api.model
    def default_get(self, default_fields):
        result = super().default_get(default_fields)
        if 'category' not in default_fields or result.get('category') == 'custom':
            if not result.get('name'):
                result['name'] = _("%s - Let's meet", self.env.user.name)
            if (not default_fields or 'staff_user_ids' in default_fields) and not result.get('staff_user_ids'):
                result['staff_user_ids'] = [Command.set(self.env.user.ids)]
        if result.get('category') == 'website':
            result['slot_ids'] = self._get_default_slots(result.get('category'))
        return result

    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Appointment Title', required=True, translate=True)
    active = fields.Boolean(default=True)

    # Technical field for backward compatibility with previous default published appointment type
    is_published = fields.Boolean('Is Published')
    category = fields.Selection([
        ('website', 'Website'),
        ('custom', 'Custom'),
        ('anytime', 'Any Time')
        ], string="Category", default="website",
        help="""Used to define this appointment type's category.\n
        Can be one of:\n
            - Website: the default category, the people can access and schedule the appointment with users from the website\n
            - Custom: the user will create and share to another user a custom appointment type with hand-picked time slots\n
            - Anytime: the user will create and share to another user an appointment type covering all their time slots""")
    min_schedule_hours = fields.Float('Schedule before (hours)', required=True, default=1.0)
    max_schedule_days = fields.Integer('Schedule not after (days)', required=True, default=15)
    min_cancellation_hours = fields.Float('Cancel Before (hours)', required=True, default=1.0)
    appointment_duration = fields.Float('Duration', required=True, default=1.0)
    appointment_duration_formatted = fields.Char(
        'Appointment Duration Formatted ', compute='_compute_appointment_duration_formatted', readonly=True,
        help='Appointment Duration formatted in words')
    reminder_ids = fields.Many2many(
        'calendar.alarm', string="Reminders",
        default=lambda self: self.env['calendar.alarm'].search([('default_for_new_appointment_type', '=', True)]))
    location_id = fields.Many2one('res.partner', string='Location')
    location = fields.Char(
        'Location formatted', compute='_compute_location', compute_sudo=True,
        help='Location formatted for one line uses')

    meeting_ids = fields.One2many('calendar.event', 'appointment_type_id', string="Appointment Meetings")

    message_confirmation = fields.Html('Confirmation Message', translate=True,
        help="Extra information provided once the appointment is booked.")
    message_intro = fields.Html('Introduction Message', translate=True,
        help="Small description of the appointment type.")

    country_ids = fields.Many2many(
        'res.country', 'appointment_type_country_rel', string='Allowed Countries',
        help="Keep empty to allow visitors from any country, otherwise you only allow visitors from selected countries")
    question_ids = fields.One2many('appointment.question', 'appointment_type_id', string='Questions', copy=True)

    slot_ids = fields.One2many('appointment.slot', 'appointment_type_id', 'Availabilities', copy=True)
    appointment_tz = fields.Selection(
        _tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz,
        help="Timezone where appointment take place")
    staff_user_ids = fields.Many2many(
        'res.users',
        'appointment_type_res_users_rel',
        domain="[('share', '=', False)]",
        string='Users',
        default=lambda self: self.env.user)
    staff_user_count = fields.Integer('# Staff Users', compute='_compute_staff_user_count')

    assign_method = fields.Selection([
        ('chosen', 'Chosen by the Customer'),
        ('random', 'Random')], string='Assignment Method', default='chosen',
        help="How users will be assigned to meetings customers book on your website.")
    appointment_count = fields.Integer('# Appointments', compute='_compute_appointment_count')
    appointment_count_report = fields.Integer(
        '# Appointments in the last 30 days', compute='_compute_appointment_count_report')
    appointment_invite_ids = fields.Many2many('appointment.invite', string='Invitation Links')
    avatars_display = fields.Selection(
        [('hide', 'No Picture'), ('show', 'Show Users\' Pictures')],
        string='Front-End Display', compute='_compute_avatars_display', readonly=False, store=True,
        help="""This option toggles the display of avatars of the staff members during the frontend appointment process.
        When choosing amongst several users, a selection screen will also be used, if website is installed.""")
    # override mail.thread for better string/help
    message_partner_ids = fields.Many2many(string='CC to',
                                           help="Contacts that need to be notified whenever a new appointment is booked or canceled, \
                                                 regardless of whether they attend or not")

    @api.depends('meeting_ids')
    def _compute_appointment_count(self):
        meeting_data = self.env['calendar.event']._read_group([('appointment_type_id', 'in', self.ids)], ['appointment_type_id'], ['appointment_type_id'])
        mapped_data = {m['appointment_type_id'][0]: m['appointment_type_id_count'] for m in meeting_data}
        for appointment_type in self:
            appointment_type.appointment_count = mapped_data.get(appointment_type.id, 0)

    @api.depends('meeting_ids')
    def _compute_appointment_count_report(self, n_days=30):
        from_n_days_ago = datetime.combine(datetime.today().date() - timedelta(days=n_days), datetime.min.time())
        until_yersterday = datetime.combine(datetime.today().date(), datetime.max.time())
        meeting_data = self.env['calendar.event']._read_group(
            [('appointment_type_id', 'in', self.ids), ('start', '>=', from_n_days_ago), ('start', '<=', until_yersterday)],
            ['appointment_type_id'], ['appointment_type_id'])
        mapped_data = {m['appointment_type_id'][0]: m['appointment_type_id_count'] for m in meeting_data}

        for appointment_type in self:
            appointment_type.appointment_count_report = mapped_data.get(appointment_type.id, 0)

    @api.depends('appointment_duration')
    def _compute_appointment_duration_formatted(self):
        for record in self:
            record.appointment_duration_formatted = self.env['ir.qweb.field.duration'].value_to_html(
                record.appointment_duration * 3600, {})

    @api.depends('category')
    def _compute_avatars_display(self):
        """ By default, enable avatars for custom appointment types and hide them for website-category ones."""
        for record in self:
            if record.category != 'website':
                record.avatars_display = 'show'
            elif not record.avatars_display:
                record.avatars_display = 'hide'

    @api.depends('location_id')
    def _compute_location(self):
        """Use location_id if available, otherwise its name, finally ''. """
        for record in self:
            if (record.location_id.contact_address or '').strip():
                record.location = ', '.join(
                    frag.strip()
                    for frag in record.location_id.contact_address.split('\n') if frag.strip()
                )
            else:
                record.location = record.location_id.name or ''

    @api.depends('staff_user_ids')
    def _compute_staff_user_count(self):
        for record in self:
            record.staff_user_count = len(record.staff_user_ids)

    @api.constrains('category', 'staff_user_ids', 'slot_ids')
    def _check_staff_user_configuration(self):
        anytime_appointments = self.search([('category', '=', 'anytime')])
        for appointment_type in self:
            if appointment_type.category != 'website' and len(appointment_type.staff_user_ids) != 1:
                raise ValidationError(_("This category of appointment type should only have one user but got %s users", len(appointment_type.staff_user_ids)))
            invalid_restricted_users = appointment_type.slot_ids.restrict_to_user_ids - appointment_type.staff_user_ids
            if invalid_restricted_users:
                raise ValidationError(_("The following users are in restricted slots but they are not part of the available staff: %s", ", ".join(invalid_restricted_users.mapped('name'))))
            if appointment_type.category == 'anytime':
                duplicate = anytime_appointments.filtered(lambda apt_type: apt_type.staff_user_ids.ids in appointment_type.staff_user_ids.ids)
                if appointment_type.ids:
                    duplicate = anytime_appointments.filtered(lambda apt_type: apt_type.id not in appointment_type.ids)
                if duplicate:
                    raise ValidationError(_("Only one anytime appointment type is allowed for a specific user."))

    @api.model_create_multi
    def create(self, vals_list):
        """ We don't want the current user to be follower of all created types """
        return super(AppointmentType, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        default['name'] = self.name + _(' (copy)')
        return super().copy(default=default)

    def action_calendar_events_reporting(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("appointment.calendar_event_action_reporting")
        action["domain"] = [('appointment_type_id', '!=', False)]
        action["context"] = {
            'search_default_appointment_type_id': self.id,
            'default_appointment_type_id': self.id,
        }
        return action

    def action_calendar_meetings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        appointments = self.meeting_ids.filtered_domain([
            ('start', '>=', datetime.today())
        ])
        nbr_appointments_week_later = appointments.filtered_domain([
            ('start', '>=', datetime.today() + timedelta(weeks=1))
        ])

        if not 'pivot' in action['view_mode']:
            action['view_mode'] = 'pivot,' + action['view_mode']
        if not any(view == 'pivot' for (_, view) in action['views']):
            action['views'].insert(0, (False, 'pivot'))

        action['context'] = {
            'default_appointment_type_id': self.id,
            'search_default_appointment_type_id': self.id,
            'default_mode': "month" if nbr_appointments_week_later else "week",
            'initial_date': appointments[0].start if appointments else datetime.today(),
        }
        return action

    def action_share_invite(self):
        return {
            'name': _('Share Link'),
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.invite',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_appointment_type_ids': self.ids,
                'dialog_size': 'medium',
            }
        }

    def action_customer_preview(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': url_join(self.get_base_url(), '/appointment/%s' % self.id),
            'target': 'self',
        }

    def action_toggle_published(self):
        for record in self:
            record.is_published = not record.is_published

    # --------------------------------------
    # Slots Generation
    # --------------------------------------

    @api.model
    def _get_default_slots(self, category):
        range_values = self._get_default_range_slots(category)
        return [
            Command.create({
                'weekday': str(weekday),
                'start_hour': start_hour,
                'end_hour': end_hour
            })
            for weekday in range(*range_values['weekday_range'])
            for (start_hour, end_hour) in range_values['hours_range']
        ]

    def _get_default_range_slots(self, category):
        '''
            If the appointment type is of category website, we set the arbitrary 'standard'
            appointment slots range (from monday to friday, 9AM-12PM and 2PM-5PM).
            If the appointment type is of category anytime, we set the slots range
            as any time between 2 arbitrary hours (monday to sunday, 7AM-7PM).
            The slot range for the anytime category will be updated in appointment_hr
            to match the user work hours.
        '''
        if category not in ['website', 'anytime']:
            raise ValueError(_("Default slots cannot be applied to the %s appointment type category.", category))
        if category == 'website':
            weekday_range = (1, 6)
            hours_range = ((9, 12), (14, 17))
        else:
            weekday_range = (1, 8)
            hours_range = ((7, 19),)
        return {
            'weekday_range': weekday_range,
            'hours_range': hours_range,
        }

    def _slots_generate(self, first_day, last_day, timezone, reference_date=None):
        """ Generate all appointment slots (in naive UTC, appointment timezone, and given (visitors) timezone)
            between first_day and last_day (datetimes in appointment timezone)

        :param datetime first_day: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime last_day: end of appointment check boundary. Timezoned to UTC;
        :param str timezone: requested timezone string e.g.: 'Europe/Brussels' or 'Etc/GMT+1'
        :param datetime reference_date: starting datetime to fetch slots. If not
          given now (in UTC) is used instead. Note that minimum schedule hours
          defined on appointment type is added to the beginning of slots;

        :return: [ {'slot': slot_record, <timezone>: (date_start, date_end), ...},
                  ... ]
        """
        if not reference_date:
            reference_date = datetime.utcnow()
        appt_tz = pytz.timezone(self.appointment_tz)
        requested_tz = pytz.timezone(timezone)
        ref_tz_apt_type = reference_date.astimezone(appt_tz)
        slots = []

        def append_slot(day, slot):
            """ Appends and generates all recurring slots. In case day is the
            reference date we adapt local_start to not append slots in the past.
            e.g. With a slot duration of 1 hour if we have slots from 8:00 to
            17:00 and we are now 9:30 for today. The first slot that we append
            should be 11:00 and not 8:00. This is necessary since we no longer
            always check based on working hours that were ignoring these past
            slots.

            :param date day: day for which we generate slots;
            :param record slot: a <appointment.slot> record
            """
            local_start = appt_tz.localize(
                datetime.combine(day,
                                 time(hour=int(slot.start_hour),
                                      minute=int(round((slot.start_hour % 1) * 60))
                                     )
                                )
            )
            # Adapt local start to not append slot in the past for today
            if local_start.date() == ref_tz_apt_type.date():
                while local_start < ref_tz_apt_type + relativedelta(hours=self.min_schedule_hours):
                    local_start += relativedelta(hours=self.appointment_duration)
            local_end = local_start + relativedelta(hours=self.appointment_duration)

            n_slot = int((slot._convert_end_hour_24_format() - (local_start.hour + local_start.minute / 60.0)) /
                         self.appointment_duration)
            for _ in range(n_slot):
                slots.append({
                    self.appointment_tz: (
                        local_start,
                        local_end,
                    ),
                    timezone: (
                        local_start.astimezone(requested_tz),
                        local_end.astimezone(requested_tz),
                    ),
                    'UTC': (
                        local_start.astimezone(pytz.UTC).replace(tzinfo=None),
                        local_end.astimezone(pytz.UTC).replace(tzinfo=None),
                    ),
                    'slot': slot,
                })
                local_start = local_end
                local_end += relativedelta(hours=self.appointment_duration)

        # We use only the recurring slot if it's not a custom appointment type.
        if self.category != 'custom':
            # Regular recurring slots (not a custom appointment), generate necessary slots using configuration rules
            slot_weekday = [int(weekday) - 1 for weekday in self.slot_ids.mapped('weekday')]
            for day in rrule.rrule(rrule.DAILY,
                                dtstart=first_day.date(),
                                until=last_day.date(),
                                byweekday=slot_weekday):
                for slot in self.slot_ids.filtered(lambda x: int(x.weekday) == day.isoweekday()):
                    append_slot(day, slot)
        else:
            # Custom appointment type, we use "unique" slots here that have a defined start/end datetime
            unique_slots = self.slot_ids.filtered(lambda slot: slot.slot_type == 'unique' and slot.end_datetime > reference_date)

            for slot in unique_slots:
                start = slot.start_datetime.astimezone(tz=None)
                end = slot.end_datetime.astimezone(tz=None)
                startUTC = start.astimezone(pytz.UTC).replace(tzinfo=None)
                endUTC = end.astimezone(pytz.UTC).replace(tzinfo=None)
                slots.append({
                    self.appointment_tz: (
                        start.astimezone(appt_tz),
                        end.astimezone(appt_tz),
                    ),
                    timezone: (
                        start.astimezone(requested_tz),
                        end.astimezone(requested_tz),
                    ),
                    'UTC': (
                        startUTC,
                        endUTC,
                    ),
                    'slot': slot,
                })
        return slots

    def _slots_available(self, slots, start_dt, end_dt, filter_users=None):
        """ Fills the slot structure with an available user

        :param list slots: slots (list of slot dict), as generated by ``_slots_generate``;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;
        :param <res.users> filter_users: filter available slots for those users (can be a singleton
          for fixed appointment types or can contain several users e.g. with random assignment and
          filters) If not set, use all users assigned to this appointment type.

        :return: None but instead update ``slots`` adding ``staff_user_id`` key
          containing found available user ID;
        """
        # shuffle the available users into a random order to avoid having the same
        # one assigned every time, force timezone
        available_users = [
            user.with_context(tz=user.tz)
            for user in (filter_users or self.staff_user_ids)
        ]
        random.shuffle(available_users)
        available_users_tz = self.env['res.users'].concat(*available_users)

        # fetch value used for availability in batch
        availability_values = self._slot_availability_prepare_values(
            available_users_tz, start_dt, end_dt
        )

        for slot in slots:
            available_staff_user = next(
                (staff_user
                 for staff_user in available_users_tz
                 if self._slot_availability_is_user_available(
                    slot,
                    staff_user,
                    availability_values
                 )),
                False)
            if available_staff_user:
                slot['staff_user_id'] = available_staff_user

    def _is_staff_user_available(self, staff_user, slot, availability_values):
        # remove me in master
        return self._slot_availability_is_user_available(slot, staff_user, availability_values)

    def _slot_availability_is_user_available(self, slot, staff_user, availability_values):
        """ This method verifies if the user is available on the given slot.
        It checks whether the user has calendar events clashing and if he
        is included in slot's restricted users.

        Can be overridden to add custom checks.

        :param dict slot: a slot as generated by ``_slots_generate``;
        :param <res.users> staff_user: user to check against slot boundaries.
          At this point timezone should be correctly set in context;
        :param dict availability_values: dict of data used for availability check.
          See ``_slot_availability_prepare_values()`` for more details;

        :return: boolean: is user available for an appointment for given slot
        """
        slot_start_dt_utc, slot_end_dt_utc = slot['UTC'][0], slot['UTC'][1]

        if slot['slot'].restrict_to_user_ids and staff_user not in slot['slot'].restrict_to_user_ids:
            return False

        partner_to_events = availability_values.get('partner_to_events') or {}
        if partner_to_events.get(staff_user.partner_id):
            for day_dt in rrule.rrule(freq=rrule.DAILY,
                                      dtstart=slot_start_dt_utc,
                                      until=slot_end_dt_utc,
                                      interval=1):
                day_events = partner_to_events[staff_user.partner_id].get(day_dt.date()) or []
                if any(event.allday or (event.start < slot_end_dt_utc and event.stop > slot_start_dt_utc) for event in day_events):
                    return False

        return True

    @api.model
    def _prepare_availability_additional_values(self, available_staff_users, first_day, last_day):
        # remove me in master
        return self._slot_availability_prepare_values(available_staff_users, first_day, last_day)

    def _slot_availability_prepare_values(self, staff_users, start_dt, end_dt):
        """ Hook method used to prepare useful values in the computation of slots
        availability. Purpose is to prepare values (event meetings notably)
        in batch instead of doing it in a loop in ``_slots_available``.

        Can be overridden to add custom values preparation to be used in custom
        overrides of ``_slot_availability_is_user_available()``.

        :param <res.users> staff_users: prepare values to check availability
          of those users against given appointment boundaries. At this point
          timezone should be correctly set in context of those users;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;

        :return: dict containing main values for computation, formatted like
          {
            'partner_to_events': meetings (not declined), based on user_partner_id
              (see ``_slot_availability_prepare_values_meetings()``);
          }
        """
        return self._slot_availability_prepare_values_meetings(staff_users, start_dt, end_dt)

    def _slot_availability_prepare_values_meetings(self, staff_users, start_dt, end_dt):
        """ This method computes meetings of users between start_dt and end_dt
        of appointment check.

        :param <res.users> staff_users: prepare values to check availability
          of those users against given appointment boundaries. At this point
          timezone should be correctly set in context of those users;
        :param datetime start_dt: beginning of appointment check boundary. Timezoned to UTC;
        :param datetime end_dt: end of appointment check boundary. Timezoned to UTC;

        :return: dict containing main values for computation, formatted like
          {
            'partner_to_events': meetings (not declined), formatted as a dict
              {
                'user_partner_id': dict of day-based meetings: {
                  'date in UTC': calendar events;
                  'date in UTC': calendar events;
                  ...
              },
              { ... }
          }
        """
        related_partners = staff_users.partner_id

        # perform a search based on start / end being set to day min / day max
        # in order to include day-long events without having to include conditions
        # on start_date and allday
        all_events = self.env['calendar.event']
        if related_partners:
            all_events = self.env['calendar.event'].search(
                ['&',
                 ('partner_ids', 'in', related_partners.ids),
                 '&',
                 ('stop', '>', datetime.combine(start_dt, time.min)),
                 ('start', '<', datetime.combine(end_dt, time.max)),
                ],
                order='start asc',
            )

        partner_to_events = {}
        for event in all_events:
            for attendee in event.attendee_ids.filtered_domain(
                    [('state', '!=', 'declined'),
                     ('partner_id', 'in', related_partners.ids)]
                ):
                for day_dt in rrule.rrule(freq=rrule.DAILY,
                                          dtstart=event.start,
                                          until=event.stop,
                                          interval=1):
                    partner_events = partner_to_events.setdefault(attendee.partner_id, {})
                    date_date = day_dt.date()  # map per day, not per hour
                    if partner_events.get(date_date):
                        partner_events[date_date] += event
                    else:
                        partner_events[date_date] = event

        return {'partner_to_events': partner_to_events}

    def _get_appointment_slots(self, timezone, filter_users=None, reference_date=None):
        """ Fetch available slots to book an appointment.

        :param str timezone: timezone string e.g.: 'Europe/Brussels' or 'Etc/GMT+1'
        :param <res.users> filter_users: filter available slots for those users (can be a singleton
          for fixed appointment types or can contain several users, e.g. with random assignment and
          filters) If not set, use all users assigned to this appointment type.
        :param datetime reference_date: starting datetime to fetch slots. If not
          given now (in UTC) is used instead. Note that minimum schedule hours
          defined on appointment type is added to the beginning of slots;

        :returns: list of dicts (1 per month) containing available slots per week
          and per day for each week (see ``_slots_generate()``), like
          [
            {'id': 0,
             'month': 'February 2022' (formatted month name),
             'weeks': [
                [{'day': '']
                [{...}],
             ],
            },
            {'id': 1,
             'month': 'March 2022' (formatted month name),
             'weeks': [ (...) ],
            },
            {...}
          ]
        """
        self.ensure_one()
        if not reference_date:
            reference_date = datetime.utcnow()

        appt_tz = pytz.timezone(self.appointment_tz)
        requested_tz = pytz.timezone(timezone)

        appointment_duration_days = self.max_schedule_days
        unique_slots = self.slot_ids.filtered(lambda slot: slot.slot_type == 'unique')

        if self.category == 'custom' and unique_slots:
            # With custom appointment type, the first day should depend on the first slot datetime
            start_first_slot = unique_slots[0].start_datetime
            first_day_utc = start_first_slot if reference_date > start_first_slot else reference_date
            first_day = requested_tz.fromutc(first_day_utc + relativedelta(hours=self.min_schedule_hours))
            appointment_duration_days = (unique_slots[-1].end_datetime.date() - reference_date.date()).days
        else:
            first_day = requested_tz.fromutc(reference_date + relativedelta(hours=self.min_schedule_hours))

        last_day = requested_tz.fromutc(reference_date + relativedelta(days=appointment_duration_days))

        # Compute available slots (ordered)
        slots = self._slots_generate(
            first_day.astimezone(appt_tz),
            last_day.astimezone(appt_tz),
            timezone,
            reference_date=reference_date
        )

        # No slots -> skip useless computation
        if not slots:
            return slots
        valid_users = filter_users.filtered(lambda user: user in self.staff_user_ids) if filter_users else None
        # Not found staff user : incorrect configuration -> skip useless computation
        if filter_users and not valid_users:
            return []
        self._slots_available(
            slots,
            first_day.astimezone(pytz.UTC),
            last_day.astimezone(pytz.UTC),
            valid_users
        )

        total_nb_slots = sum('staff_user_id' in slot for slot in slots)
        nb_slots_previous_months = 0

        # Compute calendar rendering and inject available slots
        today = requested_tz.fromutc(reference_date)
        start = slots[0][timezone][0] if slots else today
        locale = babel_locale_parse(get_lang(self.env).code)
        month_dates_calendar = cal.Calendar(locale.first_week_day).monthdatescalendar
        months = []
        while (start.year, start.month) <= (last_day.year, last_day.month):
            nb_slots_next_months = sum('staff_user_id' in slot for slot in slots)
            has_availabilities = False
            dates = month_dates_calendar(start.year, start.month)
            for week_index, week in enumerate(dates):
                for day_index, day in enumerate(week):
                    mute_cls = weekend_cls = today_cls = None
                    today_slots = []
                    if day.weekday() in (locale.weekend_start, locale.weekend_end):
                        weekend_cls = 'o_weekend'
                    if day == today.date() and day.month == today.month:
                        today_cls = 'o_today'
                    if day.month != start.month:
                        mute_cls = 'text-muted o_mute_day'
                    else:
                        # slots are ordered, so check all unprocessed slots from until > day
                        while slots and (slots[0][timezone][0].date() <= day):
                            if (slots[0][timezone][0].date() == day) and ('staff_user_id' in slots[0]):
                                slot_staff_user_id = slots[0]['staff_user_id'].id
                                slot_start_dt_tz = slots[0][timezone][0].strftime('%Y-%m-%d %H:%M:%S')
                                slot = {
                                    'datetime': slot_start_dt_tz,
                                    'staff_user_id': slot_staff_user_id,
                                }
                                if slots[0]['slot'].allday:
                                    slot_duration = 24
                                    slot.update({
                                        'hours': _("All day"),
                                        'slot_duration': slot_duration,
                                    })
                                else:
                                    start_hour = format_time(slots[0][timezone][0].time(), format='short', locale=locale)
                                    end_hour = format_time(slots[0][timezone][1].time(), format='short', locale=locale)
                                    slot_duration = str((slots[0][timezone][1] - slots[0][timezone][0]).total_seconds() / 3600)
                                    slot.update({
                                        'hours': "%s - %s" % (start_hour, end_hour) if self.category == 'custom' else start_hour,
                                        'slot_duration': slot_duration,
                                    })
                                slot['url_parameters'] = url_encode({
                                    'staff_user_id': slot_staff_user_id,
                                    'date_time': slot_start_dt_tz,
                                    'duration': slot_duration,
                                })
                                today_slots.append(slot)
                                nb_slots_next_months -= 1
                            slots.pop(0)
                    today_slots = sorted(today_slots, key=lambda d: d['datetime'])
                    dates[week_index][day_index] = {
                        'day': day,
                        'slots': today_slots,
                        'mute_cls': mute_cls,
                        'weekend_cls': weekend_cls,
                        'today_cls': today_cls
                    }

                    has_availabilities = has_availabilities or bool(today_slots)

            months.append({
                'id': len(months),
                'month': format_datetime(start, 'MMMM Y', locale=get_lang(self.env).code),
                'weeks': dates,
                'has_availabilities': has_availabilities,
                'nb_slots_previous_months': nb_slots_previous_months,
                'nb_slots_next_months': nb_slots_next_months,
            })
            nb_slots_previous_months = total_nb_slots - nb_slots_next_months
            start = start + relativedelta(months=1)
        return months
