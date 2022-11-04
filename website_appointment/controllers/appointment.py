# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.appointment.controllers.appointment import AppointmentController


class WebsiteAppointment(AppointmentController):

    # ------------------------------------------------------------
    # APPOINTMENT INDEX PAGE
    # ------------------------------------------------------------

    @http.route()
    def appointment_type_index(self, page=1, **kwargs):
        """
        Display the appointments to choose (the display depends of a custom option called 'Card Design')

        :param page: the page number displayed when the appointments are organized by cards

        A param filter_appointment_type_ids can be passed to display a define selection of appointments types.
        This param is propagated through templates to allow people to go back with the initial appointment
        types filter selection
        """
        available_appointment_types = self._fetch_available_appointments(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            kwargs.get('search')
        )
        if len(available_appointment_types) == 1 and not kwargs.get('search'):
            # If there is only one appointment type available in the selection, skip the appointment type selection view
            return request.redirect('/appointment/%s?%s' % (available_appointment_types.id, keep_query('*')))

        cards_layout = request.website.viewref('website_appointment.opt_appointments_list_cards').active

        if cards_layout:
            return request.render(
                'website_appointment.appointments_cards_layout',
                self._prepare_appointments_cards_data(
                    page, available_appointment_types,
                    **kwargs
                )
            )
        else:
            return request.render(
                'appointment.appointments_list_layout',
                self._prepare_appointments_list_data(
                    available_appointment_types,
                    **kwargs
                )
            )

    # ----------------------------------------------------------------
    # APPOINTMENT TYPE PAGE VIEW : WITH NEW OPERATOR SELECTION VIEW
    # ----------------------------------------------------------------

    def _get_appointment_type_operator_selection_view(self, appointment_type, page_values):
        """
        Renders the appointment_select_operator template. This displays a card view of available staff users to
        select from for appointment_type, containing their picture, job description and website_description.

        :param appointment_type: the appointment_type that we want to access.
        :param page_values: dict of precomputed values in the appointment_page route.
        """
        return request.render("website_appointment.appointment_select_operator", {
            'appointment_type': appointment_type,
            'available_appointments': page_values['available_appointments'],
            'main_object': appointment_type,
            'users_possible': page_values['users_possible'],
        })

    def _get_appointment_type_page_view(self, appointment_type, page_values, state=False, **kwargs):
        """
        Override: when website_appointment is installed, instead of the default appointment type page, renders the
        operator selection template, if the condition below is met.
        """
        # If the user skips the user selection to see all availabilities, make sure we do not show the selection.
        # As the operator view is mainly user cards, we only show it if avatars are 'on'. Also, it makes no sense in
        # random appointment types since it is a selection screen. Moreover, the selection should not have already
        # been made before in order to avoid loops. Finally, in order to choose, one needs at least 2 possible users.
        if not kwargs.get('skip_operator_selection') and \
                appointment_type.assign_method == 'chosen' and \
                appointment_type.avatars_display == 'show' and \
                not page_values['user_selected'] and \
                len(page_values['users_possible']) > 1:
            return self._get_appointment_type_operator_selection_view(appointment_type, page_values)
        return super()._get_appointment_type_page_view(appointment_type, page_values, state, **kwargs)

    def _prepare_appointment_type_page_values(self, appointment_type, staff_user_id=False, skip_operator_selection=False, **kwargs):
        """
        Override: Take into account the operator selection flow. When skipping the selection,
        no user_selected or user_default should be set. The display is also properly managed according to this new flow.

        :param skip_operator_selection: If true, skip the selection, and instead see all availabilities. No user should be selected.
        """
        values = super()._prepare_appointment_type_page_values(appointment_type, staff_user_id, **kwargs)
        values['skip_operator_selection'] = skip_operator_selection
        if skip_operator_selection:
            values['user_selected'] = values['user_default'] = request.env['res.users']
        else:
            values['hide_select_dropdown'] = len(values['users_possible']) <= 1 or (appointment_type.avatars_display == 'show' and values['user_selected'])
        return values

    # Tools / Data preparation
    # ------------------------------------------------------------

    def _prepare_appointments_cards_data(self, page, appointment_types=None, **kwargs):
        """
            Compute specific data for the cards layout like the the search bar and the pager.
        """
        if appointment_types is None:
            appointment_types = self._fetch_available_appointments(
                kwargs.get('filter_appointment_type_ids'),
                kwargs.get('filter_staff_user_ids'),
                kwargs.get('invite_token'),
                kwargs.get('search')
            )

        appointment_type_ids = kwargs.get('filter_appointment_type_ids')
        domain = self._appointments_base_domain(
            appointment_type_ids,
            kwargs.get('search'),
            kwargs.get('invite_token'),
        )

        website = request.website

        APPOINTMENTS_PER_PAGE = 12

        Appointment = request.env['appointment.type']
        appointment_count = len(appointment_types)

        pager = website.pager(
            url='/appointment',
            url_args=kwargs,
            total=appointment_count,
            page=page,
            step=APPOINTMENTS_PER_PAGE,
            scope=5,
        )

        # Use appointment_types to keep the sudo if needed
        appointment_types = Appointment.sudo().search(domain, limit=APPOINTMENTS_PER_PAGE, offset=pager['offset'])

        return {
            'appointment_types': appointment_types,
            'current_search': kwargs.get('search'),
            'pager': pager,
            'filter_appointment_type_ids': appointment_type_ids,
            'filter_staff_user_ids': kwargs.get('filter_staff_user_ids'),
            'invite_token': kwargs.get('invite_token'),
            'search_count': appointment_count,
        }

    def _get_customer_partner(self):
        partner = super()._get_customer_partner()
        if not partner:
            partner = request.env['website.visitor']._get_visitor_from_request().partner_id
        return partner

    @staticmethod
    def _get_customer_country():
        """
            Find the country from the geoip lib or fallback on the user or the visitor
        """
        country = super()._get_customer_country()
        if not country:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            country = visitor.country_id
        return country
