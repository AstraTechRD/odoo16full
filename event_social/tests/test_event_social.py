# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import EventCase
from odoo.exceptions import UserError
from odoo.tests import Form, users


class EventSocialCase(EventCase):

    @users('user_eventmanager')
    def test_event_mail_after_sub(self):
        """Check that we can not set "after each registration" with social event mail."""
        social_template = self.env['social.post.template'].create({'message': 'Join the Python side of the force !'})
        with self.assertRaises(UserError):
            self.env['event.type'].create({
                'name': 'Super category',
                'event_type_mail_ids': [(0, 0, {
                    'notification_type': 'social_post',
                    'template_ref': 'social.post.template,%i' % social_template.id,
                    'interval_type': 'after_sub'
                })],
            })

        with self.assertRaises(UserError):
            self.env['event.mail'].create({
                'notification_type': 'social_post',
                'template_ref': 'social.post.template,%i' % social_template.id,
                'interval_type': 'after_sub',
                'event_id': self.env['event.event'].search([])[0].id,
            })

    @users('user_eventmanager')
    def test_event_mail_before_event(self):
        """Check that the social template is automatically set, when changing the category of the event."""
        social_template = self.env['social.post.template'].create({'message': 'Join the Python side of the force !'})
        category = self.env['event.type'].create({
            'name': 'Super category',
            'event_type_mail_ids': [(0, 0, {'notification_type': 'social_post', 'template_ref': 'social.post.template,%i' % social_template.id})],
        })
        event_form = Form(self.env['event.event'])
        event_form.name = 'Test event'
        event_form.date_begin = '2020-02-01'
        event_form.date_end = '2020-02-01'
        event_form.event_type_id = category
        event = event_form.save()

        self.assertEqual(event.name, 'Test event')
        self.assertEqual(len(event.event_mail_ids), 1)
        self.assertEqual(event.event_mail_ids.notification_type, 'social_post')
        self.assertEqual(event.event_mail_ids.template_ref, social_template)
