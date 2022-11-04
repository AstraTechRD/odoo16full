# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.exceptions import ValidationError
from odoo.tests import users, tagged


@tagged('appointment')
class WAppointmentTest(AppointmentCommon, MockVisitor):

    def test_apt_type_create_from_website(self):
        """ Test that when creating an appointment type from the website, we use
        the visitor's timezone as fallback for the user's timezone """
        test_user = self.apt_manager
        test_user.write({'tz': False})

        visitor = self.env['website.visitor'].create({
            "name": 'Test Visitor',
            'access_token': test_user.partner_id.id,
            "timezone": False,
        })

        AppointmentType = self.env['appointment.type']
        with self.mock_visitor_from_request(force_visitor=visitor):
            # Test appointment timezone when user and visitor both don't have timezone
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment UTC Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment UTC Timezone')
                ]).appointment_tz, 'UTC'
            )

            # Test appointment timezone when user doesn't have timezone and visitor have timezone
            visitor.timezone = 'Europe/Brussels'
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment Visitor Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment Visitor Timezone')
                ]).appointment_tz, visitor.timezone
            )

            # Test appointment timezone when user has timezone
            test_user.tz = 'Asia/Calcutta'
            AppointmentType.with_user(test_user).create_and_get_website_url(**{'name': 'Appointment User Timezone'})
            self.assertEqual(
                AppointmentType.search([
                    ('name', '=', 'Appointment User Timezone')
                ]).appointment_tz, test_user.tz
            )

    @users('apt_manager')
    def test_apt_type_create_from_website_slots(self):
        """ Test that when creating an appointment type from the website, defaults slots are set."""
        pre_slots = self.env['appointment.slot'].search([])
        # Necessary for appointment type as `create_and_get_website_url` does not return the record.
        pre_appts = self.env['appointment.type'].search([])

        self.env['appointment.type'].create_and_get_website_url(**{
            'name': 'Test Appointment Type has slots',
            'staff_user_ids': [self.staff_user_bxls.id]
        })

        new_appt = self.env['appointment.type'].search([]) - pre_appts
        new_slots = self.env['appointment.slot'].search([]) - pre_slots
        self.assertEqual(new_slots.appointment_type_id, new_appt)

        expected_slots = {
            (str(weekday), start_hour, end_hour) : 1
            for weekday in range(1, 6)
            for start_hour, end_hour in ((9., 12.), (14., 17.))
        }
        created_slots = Counter()
        for slot in new_slots:
            created_slots[(slot.weekday, slot.start_hour, slot.end_hour)] += 1
        self.assertDictEqual(created_slots, expected_slots)

    @users('admin')
    def test_apt_type_is_published(self):
        for category, default in [
                ('custom', True),
                ('website', False),
                ('anytime', True)
            ]:
            appointment_type = self.env['appointment.type'].create({
                'name': 'Custom Appointment',
                'category': category,
            })
            self.assertEqual(appointment_type.is_published, default)

            if category in ['custom', 'website']:
                appointment_copied = appointment_type.copy()
                self.assertFalse(appointment_copied.is_published, "When we copy an appointment type, the new one should not be published")

                appointment_type.write({'is_published': False})
                appointment_copied = appointment_type.copy()
                self.assertFalse(appointment_copied.is_published)
            else:
                with self.assertRaises(ValidationError):
                    # A maximum of 1 anytime appointment per employee is allowed
                    appointment_type.copy()

    @users('admin')
    def test_apt_type_is_published_update(self):
        appointment = self.env['appointment.type'].create({
            'name': 'Website Appointment',
            'category': 'website',
        })
        self.assertFalse(appointment.is_published, "A website appointment type should not be published at creation")

        appointment.write({'category': 'custom'})
        self.assertTrue(appointment.is_published, "Modifying an appointment type category to custom auto-published it")

        appointment.write({'category': 'website'})
        self.assertFalse(appointment.is_published, "Modifying an appointment type category to website unpublished it")

        appointment.write({'category': 'anytime'})
        self.assertTrue(appointment.is_published, "Modifying an appointment type category to anytime auto-published it")
