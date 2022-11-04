# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from babel.dates import format_datetime, format_date
from datetime import datetime, timedelta
from werkzeug.urls import url_encode

from odoo import fields, _
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.calendar.controllers.main import CalendarController
from odoo.http import request, route
from odoo.tools import html2plaintext, is_html_empty
from odoo.tools.misc import get_lang


class AppointmentCalendarController(CalendarController):

    # ------------------------------------------------------------
    # CALENDAR EVENT VIEW
    # ------------------------------------------------------------

    @route(website=True)
    def view_meeting(self, token, id):
        """Redirect the internal logged in user to the form view of calendar.event, and redirect
           regular attendees to the website page of the calendar.event for online appointments"""
        super(AppointmentCalendarController, self).view_meeting(token, id)
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('event_id', '=', int(id))])
        if not attendee:
            return request.render("appointment.appointment_invalid", {})

        # If user is internal and logged, redirect to form view of event
        if request.env.user._is_internal():
            url_params = url_encode({
                'id': id,
                'view_type': 'form',
                'model': attendee.event_id._name,
            })
            return request.redirect('/web?db=%s#%s' % (request.env.cr.dbname, url_params))

        request.session['timezone'] = attendee.partner_id.tz
        if not attendee.event_id.access_token:
            attendee.event_id._generate_access_token()
        return request.redirect('/calendar/view/%s?partner_id=%s' % (attendee.event_id.access_token, attendee.partner_id.id))

    @route(['/calendar/view/<string:access_token>'], type='http', auth="public", website=True)
    def appointment_view(self, access_token, partner_id, state=False, **kwargs):
        """
        Render the validation of an appointment and display a summary of it

        :param access_token: the access_token of the event linked to the appointment
        :param state: allow to display an info message, possible values:
            - new: Info message displayed when the appointment has been correctly created
            - no-cancel: Info message displayed when an appointment can no longer be canceled
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not event:
            return request.not_found()
        timezone = request.session.get('timezone')
        if not timezone:
            timezone = request.env.context.get('tz') or event.appointment_type_id.appointment_tz or event.partner_ids and event.partner_ids[0].tz or event.user_id.tz or 'UTC'
            request.session['timezone'] = timezone
        tz_session = pytz.timezone(timezone)

        date_start_suffix = ""
        format_func = format_datetime
        if not event.allday:
            url_date_start = fields.Datetime.from_string(event.start).strftime('%Y%m%dT%H%M%SZ')
            url_date_stop = fields.Datetime.from_string(event.stop).strftime('%Y%m%dT%H%M%SZ')
            date_start = fields.Datetime.from_string(event.start).replace(tzinfo=pytz.utc).astimezone(tz_session)
        else:
            url_date_start = url_date_stop = fields.Date.from_string(event.start_date).strftime('%Y%m%d')
            date_start = fields.Date.from_string(event.start_date)
            format_func = format_date
            date_start_suffix = _(', All Day')

        locale = get_lang(request.env).code
        day_name = format_func(date_start, 'EEE', locale=locale)
        date_start = day_name + ' ' + format_func(date_start, locale=locale) + date_start_suffix
        # convert_online_event_desc_to_text method for correct data formatting in external calendars
        details = event.appointment_type_id and event.appointment_type_id.message_confirmation or event.convert_online_event_desc_to_text(event.description) or ''
        params = {
            'action': 'TEMPLATE',
            'text': event.name,
            'dates': url_date_start + '/' + url_date_stop,
            'details': html2plaintext(details.encode('utf-8'))
        }
        if event.location:
            params.update(location=event.location.replace('\n', ' '))
        encoded_params = url_encode(params)
        google_url = 'https://www.google.com/calendar/render?' + encoded_params

        return request.render("appointment.appointment_validated", {
            'event': event,
            'datetime_start': date_start,
            'google_url': google_url,
            'state': state,
            'partner_id': partner_id,
            'is_html_empty': is_html_empty,
        })

    @route(['/calendar/cancel/<string:access_token>',
            '/calendar/<string:access_token>/cancel',
           ], type='http', auth="public", website=True)
    def appointment_cancel(self, access_token, partner_id, **kwargs):
        """
            Route to cancel an appointment event, this route is linked to a button in the validation page
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        appointment_type = event.appointment_type_id
        appointment_invite = event.appointment_invite_id
        if not event:
            return request.not_found()
        if fields.Datetime.from_string(event.allday and event.start_date or event.start) < datetime.now() + timedelta(hours=event.appointment_type_id.min_cancellation_hours):
            return request.redirect('/calendar/view/' + access_token + '?state=no-cancel&partner_id=%s' % partner_id)
        event.sudo().action_cancel_meeting([int(partner_id)])
        if appointment_invite:
            redirect_url = "%s&state=cancel" % appointment_invite.redirect_url
        else:
            redirect_url = '/appointment/%s?%s' % (appointment_type.id, keep_query('*', state="cancel"))
        return request.redirect(redirect_url)

    @route(['/calendar/ics/<string:access_token>.ics'], type='http', auth="public", website=True)
    def appointment_get_ics_file(self, access_token, **kwargs):
        """
            Route to add the appointment event in a iCal/Outlook calendar
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not event or not event.attendee_ids:
            return request.not_found()
        files = event._get_ics_file()
        content = files[event.id]
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', 'attachment; filename=Appoinment.ics')
        ])
