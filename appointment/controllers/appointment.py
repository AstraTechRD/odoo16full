# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pytz
import re
import uuid

from babel.dates import format_datetime, format_date, format_time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_encode

from odoo import exceptions, http, fields, _
from odoo.http import request, route
from odoo.osv import expression
from odoo.tools import plaintext2html, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.http_routing.models.ir_http import unslug

def _formated_weekdays(locale):
    """ Return the weekdays' name for the current locale
        from Mon to Sun.
        :param locale: locale
    """
    formated_days = [
        format_date(date(2021, 3, day), 'EEE', locale=locale)
        for day in range(1, 8)
    ]
    # Get the first weekday based on the lang used on the website
    first_weekday_index = babel_locale_parse(locale).first_week_day
    # Reorder the list of days to match with the first weekday
    formated_days = list(formated_days[first_weekday_index:] + formated_days)[:7]
    return formated_days

class AppointmentController(http.Controller):

    # ------------------------------------------------------------
    # APPOINTMENT INVITATION
    # ------------------------------------------------------------

    @route(['/book/<string:short_code>'],
            type='http', auth="public", website=True)
    def appointment_invite(self, short_code):
        """
        Invitation link that simplify the URL sent or shared to partners.
        This will redirect to a correct URL with the params selected with the
        invitation.
        """
        invitation = request.env['appointment.invite'].sudo().search([('short_code', '=', short_code)])
        if not invitation:
            raise NotFound()
        return request.redirect(invitation.redirect_url)

    # ------------------------------------------------------------
    # APPOINTMENT INDEX PAGE
    # ------------------------------------------------------------

    @route(['/calendar', '/calendar/page/<int:page>'],
            type='http', auth="public", website=True, sitemap=True)
    def appointment_type_index_old(self, page=1, **kwargs):
        """ For backward compatibility """
        return request.redirect(
            '/appointment%s?%s' % ('/page/%s' % page if page != 1 else '', url_encode(kwargs)),
            code=301,
        )

    @route(['/appointment', '/appointment/page/<int:page>'],
           type='http', auth="public", website=True, sitemap=True)
    def appointment_type_index(self, page=1, **kwargs):
        """
        Display the appointments to choose (the display depends of a custom option called 'Card Design')

        :param page: the page number displayed when the appointments are organized by cards

        A param filter_appointment_type_ids can be passed to display a define selection of appointments types.
        This param is propagated through templates to allow people to go back with the initial appointment
        types filter selection
        """
        return request.render('appointment.appointments_list_layout', self._prepare_appointments_list_data(**kwargs))

    # Tools / Data preparation
    # ------------------------------------------------------------

    @staticmethod
    def _fetch_available_appointments(appointment_types, staff_users, invite_token, search=None):
        """Fetch the available appointment types

        :param recordset appointment_types: Record set of appointment types for
            the filter linked to the appointment types
        :param recordset staff_users: Record set of users for the filter linked
            to the staff users
        :param str invite_token: token of the appointment invite
        :param str search: search bar value used to compute the search domain
        """
        return AppointmentController._fetch_and_check_private_appointment_types(
            appointment_types, staff_users, invite_token,
            domain=AppointmentController._appointments_base_domain(
                appointment_types, search, invite_token
            )
        )

    def _prepare_appointments_list_data(self, appointment_types=None, **kwargs):
        """Compute specific data used to render the list layout

        :param recordset appointment_types: Record set of appointments to show.
            If not provided, fetch them using _fetch_available_appointments
        """
        appointment_types = appointment_types or self._fetch_available_appointments(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
        )
        return {
            'appointment_types': appointment_types,
            'invite_token': kwargs.get('invite_token'),
            'filter_appointment_type_ids': kwargs.get('filter_appointment_type_ids'),
            'filter_staff_user_ids': kwargs.get('filter_staff_user_ids'),
        }

    @staticmethod
    def _appointments_base_domain(filter_appointment_type_ids, search=False, invite_token=False):
        domain = [('category', '=', 'website')]

        if filter_appointment_type_ids:
            domain = expression.AND([domain, [('id', 'in', json.loads(filter_appointment_type_ids))]])

        if not invite_token:
            country = AppointmentController._get_customer_country()
            if country:
                country_domain = ['|', ('country_ids', '=', False), ('country_ids', 'in', [country.id])]
                domain = expression.AND([domain, country_domain])

        # Add domain related to the search bar
        if search:
            domain = expression.AND([domain, [('name', 'ilike', search)]])

        # Because of sudo search, we need to search only published ones if there is no invite_token
        if request.env.user.share and not invite_token:
            domain = expression.AND([domain, [('is_published', '=', True)]])

        return domain

    # ------------------------------------------------------------
    # APPOINTMENT TYPE PAGE VIEW
    # ------------------------------------------------------------

    @route(['/calendar/<string:appointment_type>'],
            type='http', auth="public", website=True, sitemap=True)
    def appointment_type_page_old(self, appointment_type, **kwargs):
        """ For backward compatibility:
        appointment_type is transformed from a recordset to a string because we removed the rights for public user.
        """
        return request.redirect('/appointment/%s?%s' % (unslug(appointment_type)[1], keep_query('*')), code=301)

    @route(['/appointment/<int:appointment_type_id>'],
           type='http', auth="public", website=True, sitemap=True)
    def appointment_type_page(self, appointment_type_id, state=False, staff_user_id=False, **kwargs):
        """
        This route renders the appointment page: It first computes a dict of values useful for all potential
        views and to choose between them in _get_appointment_type_page_view, that renders the chosen one.

        :param appointment_type_id: the appointment_type_id of the appointment type that we want to access
        :param state: the type of message that will be displayed in case of an error/info. Possible values:
            - cancel: Info message to confirm that an appointment has been canceled
            - failed-staff-user: Error message displayed when the slot has been taken while doing the registration
            - failed-partner: Info message displayed when the partner has already an event in the time slot selected
        :param staff_user_id: id of the selected user, from upstream or coming back from an error.
        """
        appointment_type = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            current_appointment_type_id=int(appointment_type_id),
        )
        if not appointment_type:
            raise NotFound()

        page_values = self._prepare_appointment_type_page_values(appointment_type, staff_user_id, **kwargs)
        return self._get_appointment_type_page_view(appointment_type, page_values, state, **kwargs)

    def _get_appointment_type_page_view(self, appointment_type, page_values, state=False, **kwargs):
        """
        Renders the appointment information alongside the calendar for the slot selection, after computation of
        the slots and preparation of other values, depending on the arguments values. This is the method to override
        in order to select another view for the appointment page.

        :param appointment_type: the appointment type that we want to access.
        :param page_values: dict containing common appointment page values. See _prepare_appointment_type_page_values for details.
        :param state: the type of message that will be displayed in case of an error/info. See appointment_type_page.
        """
        request.session.timezone = self._get_default_timezone(appointment_type)
        slots = appointment_type._get_appointment_slots(
            request.session['timezone'],
            filter_users=page_values['user_selected'] or page_values['user_default'] or page_values['users_possible'],
        )
        formated_days = _formated_weekdays(get_lang(request.env).code)
        month_first_available = next((month['id'] for month in slots if month['has_availabilities']), False)

        render_params = dict({
            'appointment_type': appointment_type,
            'is_html_empty': is_html_empty,
            'formated_days': formated_days,
            'main_object': appointment_type,
            'month_first_available': month_first_available,
            'month_kept_from_update': False,
            'slots': slots,
            'state': state,
            'timezone': request.session['timezone'],  # bw compatibility
        }, **page_values
        )
        return request.render("appointment.appointment_info", render_params)

    def _prepare_appointment_type_page_values(self, appointment_type, staff_user_id=False, **kwargs):
        """ Computes all values needed to choose between / common to all appointment_type page templates.

        :return: a dict containing:
            - available_appointments: all available appointments according to current filters and invite tokens.
            - filter_appointment_type_ids, filter_staff_user_ids and invite_token parameters.
            - user_default: the first of possible staff users. It will be selected by default (in the user select dropdown)
            if no user_selected. Otherwise, the latter will be preselected instead. It is only set if there is at least one
            possible user and if the choice is activated in appointment_type.
            - user_selected: the user corresponding to staff_user_id in the url and to the selected one. It can be selected
            upstream, from the operator_select screen (see WebsiteAppointment controller), or coming back from an error.
            It is only set if among the possible users.
            - users_possible: all possible staff users considering filter_staff_user_ids and staff members of appointment_type.
            - hide_select_dropdown: True if the user select dropdown should be hidden. (e.g. an operator has been selected before)
            Even if hidden, it can still be in the view and used to update availabilities according to the selected user in the js.
        """
        filter_staff_user_ids = json.loads(kwargs.get('filter_staff_user_ids') or '[]')
        users_possible = self._get_possible_staff_users(appointment_type, filter_staff_user_ids)
        user_default = user_selected = request.env['res.users']
        staff_user_id = int(staff_user_id) if staff_user_id else False

        if appointment_type.assign_method == 'chosen' and users_possible:
            if staff_user_id and staff_user_id in users_possible.ids:
                user_selected = next(user for user in users_possible if user.id == staff_user_id)
            user_default = users_possible[0]

        return {
            'available_appointments': self._fetch_available_appointments(
                kwargs.get('filter_appointment_type_ids'),
                kwargs.get('filter_staff_user_ids'),
                kwargs.get('invite_token')
            ),
            'filter_appointment_type_ids': kwargs.get('filter_appointment_type_ids'),
            'filter_staff_user_ids': kwargs.get('filter_staff_user_ids'),
            'hide_select_dropdown': len(users_possible) <= 1,
            'invite_token': kwargs.get('invite_token'),
            'user_default': user_default,
            'user_selected': user_selected,
            'users_possible': users_possible
        }

    # Staff User tools
    # ------------------------------------------------------------

    @http.route('/appointment/<int:appointment_type_id>/avatar', type='http', auth="public", cors="*")
    def appointment_staff_user_avatar(self, appointment_type_id, user_id=False, avatar_size=512):
        """
        Route used to bypass complicated access rights like 'website_published'. We consider we can display the avatar
        of the user of id user_id if it belongs to the appointment_type_id and if the option avatars_display is set to 'show'
        for that appointment type. In that case we consider that the avatars can be made public. Default field is avatar_512.
        Another avatar_size corresponding to an existing avatar field on res.users can be given as route parameter.
        """
        user = request.env['res.users'].sudo().browse(int(user_id))
        appointment_type = request.env['appointment.type'].sudo().browse(appointment_type_id)

        user = user if appointment_type.avatars_display == 'show' and user in appointment_type.staff_user_ids else request.env['res.users']
        return request.env['ir.binary']._get_image_stream_from(
            user,
            field_name='avatar_%s' % (avatar_size if int(avatar_size) in [128, 256, 512, 1024, 1920] else 512),
            placeholder='mail/static/src/img/smiley/avatar.jpg',
        ).get_response()

    def _get_possible_staff_users(self, appointment_type, filter_staff_user_ids):
        """
        This method filters the staff members of given appointment_type using filter_staff_user_ids that are possible to pick.
        If no filter exist and assign method is 'chosen', we allow all users existing on the appointment type.

        :param appointment_type_id: the appointment_type_id of the appointment type that we want to access
        :param filter_staff_user_ids: list of user ids used to filter the ones of the appointment_type.
        :return: a res.users recordset containing all possible staff users to choose from.
        """
        if appointment_type.assign_method == 'chosen' and not filter_staff_user_ids:
            return appointment_type.staff_user_ids
        return appointment_type.staff_user_ids.filtered(lambda staff_user: staff_user.id in filter_staff_user_ids)

    # Tools / Data preparation
    # ------------------------------------------------------------

    @staticmethod
    def _fetch_and_check_private_appointment_types(appointment_type_ids, staff_user_ids, invite_token, current_appointment_type_id=False, domain=False):
        """
        When an invite_token is in the params, we need to check if the params used and the ones in the invitation are
        the same.
        For the old link, we use the technical field "is_published" to determine if a user had previous access.
        Check finally if we have the rights on the appointment_types. If the token is correct then we continue, if not
        we raise an Forbidden error. We return the current appointment type displayed/used if one or the appointment types
        linked to the filter in the url param
        :param recordset appointment_types: Record set of appointment types for the filter linked to the appointment types
        :param recordset staff_users: Record set of users for the filter linked to the staff users
        :param str invite_token: token of the appointment invite
        :param int current_appointment_type_id: appointment type id currently used/displayed, used as fallback if there is no appointment type filter
        :param domain: a search domain used when displaying the available appointment types
        """
        appointment_type_ids = json.loads(appointment_type_ids or "[]")
        if not appointment_type_ids and current_appointment_type_id:
            appointment_type_ids = [current_appointment_type_id]
        if not appointment_type_ids and domain:
            appointment_type_ids = request.env['appointment.type'].sudo().search(domain).ids
        elif not appointment_type_ids:
            raise ValueError()

        # Check that the current appointment type is include in the filter
        if current_appointment_type_id and current_appointment_type_id not in appointment_type_ids:
            raise ValueError()

        appointment_types = request.env['appointment.type'].browse(appointment_type_ids).exists()
        staff_users = request.env['res.users'].sudo().browse(json.loads(staff_user_ids or "[]"))

        if invite_token:
            appt_invite = request.env['appointment.invite'].sudo().search([('access_token', '=', invite_token)])
            if not appt_invite or not appt_invite._check_appointments_params(appointment_types, staff_users):
                raise Forbidden()
            # To bypass the access checks in case we are public user
            appointment_types = appointment_types.sudo()
        elif request.env.user.share:
            # Backward compatibility for old version that had their appointment types "published" by default (aka accessible with read access rights)
            appointment_types = appointment_types.sudo().filtered('is_published') or appointment_types

        try:
            appointment_types.check_access_rights('read')
            appointment_types.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()

        current_appointment_type = request.env['appointment.type'].sudo().browse(current_appointment_type_id) if current_appointment_type_id else False
        if current_appointment_type:
            return current_appointment_type
        if domain:
            appointment_types = appointment_types.filtered_domain(domain)
        return appointment_types

    # ------------------------------------------------------------
    # APPOINTMENT TYPE BOOKING
    # ------------------------------------------------------------

    @http.route(['/appointment/<int:appointment_type_id>/info'],
                type='http', auth="public", website=True, sitemap=False)
    def appointment_type_id_form(self, appointment_type_id, staff_user_id, date_time, duration, **kwargs):
        """
        Render the form to get information about the user for the appointment

        :param appointment_type_id: the appointment type id related
        :param staff_user_id: the user selected for the appointment
        :param date_time: the slot datetime selected for the appointment
        :param duration: the duration of the slot
        :param filter_appointment_type_ids: see ``Appointment.appointments()`` route
        """
        appointment_type = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            current_appointment_type_id=int(appointment_type_id),
        )
        if not appointment_type:
            raise NotFound()
        partner = self._get_customer_partner()
        partner_data = partner.read(fields=['name', 'mobile', 'email'])[0] if partner else {}
        date_time_object = datetime.strptime(date_time, dtf)
        day_name = format_datetime(date_time_object, 'EEE', locale=get_lang(request.env).code)
        date_formated = format_date(date_time_object.date(), locale=get_lang(request.env).code)
        time_locale = format_time(date_time_object.time(), locale=get_lang(request.env).code, format='short')
        return request.render("appointment.appointment_form", {
            'partner_data': partner_data,
            'appointment_type': appointment_type,
            'available_appointments': self._fetch_available_appointments(
                kwargs.get('filter_appointment_type_ids'),
                kwargs.get('filter_staff_user_ids'),
                kwargs.get('invite_token'),
            ),
            'main_object': appointment_type,
            'datetime': date_time,
            'date_locale': day_name + ' ' + date_formated,
            'time_locale': time_locale,
            'datetime_str': date_time,
            'duration_str': duration,
            'duration': float(duration),
            'staff_user': request.env['res.users'].browse(int(staff_user_id)),
            'timezone': request.session['timezone'] or appointment_type.timezone,  # bw compatibility
            'users_possible': self._get_possible_staff_users(appointment_type, json.loads(kwargs.get('filter_staff_user_ids') or '[]')),
        })

    @http.route(['/appointment/<int:appointment_type_id>/submit'],
                type='http', auth="public", website=True, methods=["POST"])
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs):
        """
        Create the event for the appointment and redirect on the validation page with a summary of the appointment.

        :param appointment_type_id: the appointment type id related
        :param datetime_str: the string representing the datetime
        :param staff_user_id: the user selected for the appointment
        :param name: the name of the user sets in the form
        :param phone: the phone of the user sets in the form
        :param email: the email of the user sets in the form
        """
        appointment_type = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            current_appointment_type_id=int(appointment_type_id),
        )
        if not appointment_type:
            raise NotFound()
        timezone = request.session.get('timezone') or appointment_type.appointment_tz
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc).replace(tzinfo=None)
        duration = float(duration_str)
        date_end = date_start + relativedelta(hours=duration)
        invite_token = kwargs.get('invite_token')

        # check availability of the selected user again (in case someone else booked while the client was entering the form)
        staff_user = request.env['res.users'].sudo().browse(int(staff_user_id)).exists()
        if staff_user not in appointment_type.sudo().staff_user_ids:
            raise NotFound()
        if staff_user and not staff_user.partner_id.calendar_verify_availability(date_start, date_end):
            return request.redirect('/appointment/%s?%s' % (appointment_type.id, keep_query('*', state='failed-staff-user')))

        Partner = self._get_customer_partner() or request.env['res.partner'].sudo().search([('email', '=like', email)], limit=1)
        if Partner:
            if not Partner.calendar_verify_availability(date_start, date_end):
                return request.redirect('/appointment/%s?%s' % (appointment_type.id, keep_query('*', state='failed-partner')))
            if not Partner.mobile:
                Partner.write({'mobile': phone})
            if not Partner.email:
                Partner.write({'email': email})
        else:
            Partner = Partner.create({
                'name': name,
                'mobile': Partner._phone_format(phone, country=AppointmentController._get_customer_country()),
                'email': email,
                'lang': request.lang.code,
            })

        # partner_inputs dictionary structures all answer inputs received on the appointment submission: key is question id, value
        # is answer id (as string) for choice questions, text input for text questions, array of ids for multiple choice questions.
        partner_inputs = {}
        appointment_question_ids = appointment_type.question_ids.ids
        for k_key, k_value in [item for item in kwargs.items() if item[1]]:
            question_id_str = re.match(r"\bquestion_([0-9]+)\b", k_key)
            if question_id_str and int(question_id_str.group(1)) in appointment_question_ids:
                partner_inputs[int(question_id_str.group(1))] = k_value
                continue
            checkbox_ids_str = re.match(r"\bquestion_([0-9]+)_answer_([0-9]+)\b", k_key)
            if checkbox_ids_str:
                question_id, answer_id = [int(checkbox_ids_str.group(1)), int(checkbox_ids_str.group(2))]
                if question_id in appointment_question_ids:
                    partner_inputs[question_id] = partner_inputs.get(question_id, []) + [answer_id]

        # The answer inputs will be created in _prepare_calendar_values from the values in question_answer_inputs
        question_answer_inputs = []
        base_answer_input_vals = {
            'appointment_type_id': appointment_type.id,
            'partner_id': Partner.id,
        }
        description_bits = []
        description = ''

        if phone:
            description_bits.append(_('Mobile: %s', phone))
        if email:
            description_bits.append(_('Email: %s', email))

        for question in appointment_type.question_ids.filtered(lambda question: question.id in partner_inputs.keys()):
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda answer: answer.id in partner_inputs[question.id])
                question_answer_inputs.extend([
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=answer.id) for answer in answers
                ])
                description_bits.append('%s: %s' % (question.name, ', '.join(answers.mapped('name'))))
            elif question.question_type in ['select', 'radio']:
                question_answer_inputs.append(
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=int(partner_inputs[question.id]))
                )
                selected_answer = question.answer_ids.filtered(lambda answer: answer.id == int(partner_inputs[question.id]))
                description_bits.append('%s: %s' % (question.name, selected_answer.name))
            elif question.question_type == 'char':
                question_answer_inputs.append(
                    dict(base_answer_input_vals, question_id=question.id, value_text_box=partner_inputs[question.id].strip())
                )
                description_bits.append('%s: %s' % (question.name, partner_inputs[question.id].strip()))
            elif question.question_type == 'text':
                question_answer_inputs.append(
                    dict(base_answer_input_vals, question_id=question.id, value_text_box=partner_inputs[question.id].strip())
                )
                description_bits.append('%s:<br/>%s' % (question.name, plaintext2html(partner_inputs[question.id].strip())))

        if description_bits:
            description = '<ul>' + ''.join(['<li>%s</li>' % bit for bit in description_bits]) + '</ul>'

        # FIXME AWA/TDE double check this and/or write some tests to ensure behavior
        # The 'mail_notify_author' is only placed here and not in 'calendar.attendee#_send_mail_to_attendees'
        # Because we only want to notify the author in the context of Online Appointments
        # When creating a meeting from your own calendar in the backend, there is no need to notify yourself
        event = request.env['calendar.event'].with_context(
            mail_notify_author=True,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            allowed_company_ids=staff_user.company_ids.ids,
        ).sudo().create(
            self._prepare_calendar_values(appointment_type, date_start, date_end, duration, description, question_answer_inputs, name, staff_user, Partner, invite_token)
        )
        event.attendee_ids.write({'state': 'accepted'})
        return request.redirect('/calendar/view/%s?partner_id=%s&%s' % (event.access_token, Partner.id, keep_query('*', state='new')))

    # Tools / Data preparation
    # ------------------------------------------------------------

    def _get_customer_partner(self):
        partner = request.env['res.partner']
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
        return partner

    @staticmethod
    def _get_customer_country():
        """
            Find the country from the geoip lib or fallback on the user or the visitor
        """
        country_code = request.geoip.get('country_code')
        country = request.env['res.country']
        if country_code:
            country = country.search([('code', '=', country_code)])
        if not country:
            country = request.env.user.country_id if not request.env.user._is_public() else country
        return country

    def _get_default_timezone(self, appointment_type):
        """
            Find the default timezone from the geoip lib or fallback on the user or the visitor
        """
        if appointment_type.location_id:
            return appointment_type.appointment_tz
        return request.httprequest.cookies.get('tz', appointment_type.appointment_tz)

    def _prepare_calendar_values(self, appointment_type, date_start, date_end, duration, description, question_answer_inputs, name, staff_user, partner, invite_token):
        """
        prepares all values needed to create a new calendar.event
        """
        categ_id = request.env.ref('appointment.calendar_event_type_data_online_appointment')
        alarm_ids = appointment_type.reminder_ids and [(6, 0, appointment_type.reminder_ids.ids)] or []
        partner_ids = list(set([staff_user.partner_id.id] + [partner.id]))
        if invite_token:
            appointment_invite_id = request.env['appointment.invite'].sudo().search([('access_token', '=', invite_token)]).id
        else:
            appointment_invite_id = False
        calendar_event_values = {
            'name': _('%s with %s', appointment_type.name, name),
            'start': date_start.strftime(dtf),
            # FIXME master
            # we override here start_date(time) value because they are not properly
            # recomputed due to ugly overrides in event.calendar (reccurrencies suck!)
            #     (fixing them in stable is a pita as it requires a good rewrite of the
            #      calendar engine)
            'start_date': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'allday': False,
            'duration': duration,
            'description': description,
            'alarm_ids': alarm_ids,
            'location': appointment_type.location,
            'partner_ids': [(4, pid, False) for pid in partner_ids],
            'categ_ids': [(4, categ_id.id, False)],
            'appointment_type_id': appointment_type.id,
            'appointment_answer_input_ids': [(0, 0, answer_input_values) for answer_input_values in question_answer_inputs],
            'user_id': staff_user.id,
            'appointment_invite_id': appointment_invite_id,
        }
        if not appointment_type.location_id:
            CalendarEvent = request.env['calendar.event']
            access_token = uuid.uuid4().hex
            calendar_event_values.update({
                'access_token': access_token,
                'videocall_location': f'{CalendarEvent.get_base_url()}/{CalendarEvent.DISCUSS_ROUTE}/{access_token}',
            })

        return calendar_event_values

    # ------------------------------------------------------------
    # APPOINTMENT TYPE JSON DATA
    # ------------------------------------------------------------

    @http.route(['/appointment/<int:appointment_type_id>/get_message_intro'],
                type="json", auth="public", methods=['POST'], website=True)
    def get_appointment_message_intro(self, appointment_type_id, **kwargs):
        appointment_type = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            current_appointment_type_id=int(appointment_type_id),
        )
        if not appointment_type:
            raise NotFound()

        return appointment_type.message_intro or ''

    @http.route(['/appointment/<int:appointment_type_id>/update_available_slots'],
                type="json", auth="public", website=True)
    def appointment_update_available_slots(self, appointment_type_id, staff_user_id=None, timezone=None, **kwargs):
        """
            Route called when the selected user or the timezone is modified to adapt the possible slots accordingly
        """
        appointment_type = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            current_appointment_type_id=int(appointment_type_id),
        )
        if not appointment_type:
            raise ValueError()

        request.session['timezone'] = timezone or appointment_type.appointment_tz
        filter_staff_user_ids = json.loads(kwargs.get('filter_staff_user_ids') or '[]')
        # If no staff_user_id is set, use only the filtered staff users to compute slots.
        if staff_user_id:
            filter_users = request.env['res.users'].sudo().browse(int(staff_user_id))
        else:
            filter_users = self._get_possible_staff_users(appointment_type, filter_staff_user_ids)
        slots = appointment_type.sudo()._get_appointment_slots(request.session['timezone'], filter_users)
        month_first_available = next((month['id'] for month in slots if month['has_availabilities']), False)
        month_before_update = kwargs.get('month_before_update')
        month_kept_from_update = next((month['id'] for month in slots if month['month'] == month_before_update), False) if month_before_update else False
        formated_days = _formated_weekdays(get_lang(request.env).code)

        return request.env['ir.qweb']._render('appointment.appointment_calendar', {
            'appointment_type': appointment_type,
            'available_appointments': self._fetch_available_appointments(
                kwargs.get('filter_appointment_type_ids'),
                kwargs.get('filter_staff_user_ids'),
                kwargs.get('invite_token')
            ),
            'timezone': request.session['timezone'],
            'formated_days': formated_days,
            'slots': slots,
            'month_kept_from_update': month_kept_from_update,
            'month_first_available': month_first_available,
        })
