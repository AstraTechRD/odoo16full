# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import random

from unittest.mock import patch

from odoo import fields
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.social.tests.common import SocialCase
from odoo.addons.social_push_notifications.models.social_account import SocialAccountPushNotifications


class SocialPushNotificationsCase(SocialCase, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super(SocialPushNotificationsCase, cls).setUpClass()
        cls.social_accounts.write({
            'firebase_use_own_account': True,
            'firebase_admin_key_file': base64.b64encode(b'{}')
        })

    def test_post(self):
        """ Test a full flow of posting social_push_notifications.
        We trigger the send method of the post and check that it does all the way to the Firebase
        sending calls. """

        # Create some visitors with or without push_token in different timezone (or no timezone)
        timezones = ['Europe/Brussels', 'America/New_York', 'Asia/Vladivostok', False]
        Visitor = self.env['website.visitor']
        visitor_vals = []
        for i in range(0, 4):
            visitor_vals.append({
                'name': timezones[i] or 'Visitor',
                'timezone': timezones[i],
                'access_token': '%032x' % random.randrange(16**32),
                'push_subscription_ids': [(0, 0, {'push_token': 'fake_token_%s' % i})] if i != 0 else False,
            })
        visitors = Visitor.create(visitor_vals)
        self.social_post.create_uid.write({'tz': timezones[0]})

        scheduled_date = fields.Datetime.now() - datetime.timedelta(minutes=1)
        with self.capture_triggers('social.ir_cron_post_scheduled') as captured_triggers:
            self.social_post.write({
                'use_visitor_timezone': True,
                'post_method': 'scheduled',
                'scheduled_date': scheduled_date
            })

        # when scheduling, a CRON trigger is created to match the scheduled_date
        self.assertEqual(len(captured_triggers.records), 1)
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(captured_trigger.call_at, scheduled_date)
        self.assertEqual(captured_trigger.cron_id, self.env.ref('social.ir_cron_post_scheduled'))

        self.assertEqual(self.social_post.state, 'draft')

        with self.capture_triggers('social.ir_cron_post_scheduled') as captured_triggers:
            self.social_post._action_post()  # begin the post process

        # as the post_method is 'scheduled', a CRON trigger should not be created, we already have one
        self.assertEqual(len(captured_triggers.records), 0)

        # check that live posts are correctly created
        live_posts = self.env['social.live.post'].search([('post_id', '=', self.social_post.id)])
        self.assertEqual(len(live_posts), 2)

        self.assertTrue(all(live_post.state == 'ready' for live_post in live_posts))
        self.assertEqual(self.social_post.state, 'posting')

        with patch.object(
             SocialAccountPushNotifications,
             '_firebase_send_message_from_configuration',
             lambda self, data, visitors: visitors.mapped('push_subscription_ids.push_token'), []):
            live_posts._post_push_notifications()

        self.assertFalse(all(live_post.state == 'posted' for live_post in live_posts))
        self.assertEqual(self.social_post.state, 'posting')

        # simulate that everyone can receive the push notif (because their time >= time of the one who created the post)
        visitors.write({'timezone': self.env.user.tz})

        with patch.object(
             SocialAccountPushNotifications,
             '_firebase_send_message_from_configuration',
             lambda self, data, visitors: visitors.mapped('push_subscription_ids.push_token'), []):
            live_posts._post_push_notifications()

        self._checkPostedStatus(True)

    @classmethod
    def _get_social_media(cls):
        return cls.env.ref('social_push_notifications.social_media_push_notifications')
