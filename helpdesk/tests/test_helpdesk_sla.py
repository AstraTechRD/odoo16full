# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch
from dateutil.relativedelta import relativedelta
from datetime import datetime
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests.common import TransactionCase

NOW = datetime(2018, 10, 10, 9, 18)
NOW2 = datetime(2019, 1, 8, 9, 0)


class HelpdeskSLA(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(HelpdeskSLA, cls).setUpClass()

        # we create a helpdesk user and a manager
        Users = cls.env['res.users'].with_context(tracking_disable=True)
        cls.main_company_id = cls.env.ref('base.main_company').id
        cls.helpdesk_manager = Users.create({
            'company_id': cls.main_company_id,
            'name': 'Helpdesk Manager',
            'login': 'hm',
            'email': 'hm@example.com',
            'groups_id': [(6, 0, [cls.env.ref('helpdesk.group_helpdesk_manager').id])]
        })
        cls.helpdesk_user = Users.create({
            'company_id': cls.main_company_id,
            'name': 'Helpdesk User',
            'login': 'hu',
            'email': 'hu@example.com',
            'groups_id': [(6, 0, [cls.env.ref('helpdesk.group_helpdesk_user').id])]
        })
        # the manager defines a team for our tests (the .sudo() at the end is to avoid potential uid problems)
        cls.test_team = cls.env['helpdesk.team'].with_user(cls.helpdesk_manager).create({
            'name': 'Test Team',
            'use_sla': True
        }).sudo()
        # He then defines its stages
        stage_as_manager = cls.env['helpdesk.stage'].with_user(cls.helpdesk_manager)
        cls.stage_new = stage_as_manager.create({
            'name': 'New',
            'sequence': 10,
            'team_ids': [(4, cls.test_team.id, 0)],
        })
        cls.stage_progress = stage_as_manager.create({
            'name': 'In Progress',
            'sequence': 20,
            'team_ids': [(4, cls.test_team.id, 0)],
        })
        cls.stage_wait = stage_as_manager.create({
            'name': 'Waiting',
            'sequence': 25,
            'team_ids': [(4, cls.test_team.id, 0)],
        })
        cls.stage_done = stage_as_manager.create({
            'name': 'Done',
            'sequence': 30,
            'team_ids': [(4, cls.test_team.id, 0)],
            'fold': True,
        })
        cls.stage_cancel = stage_as_manager.create({
            'name': 'Cancelled',
            'sequence': 40,
            'team_ids': [(4, cls.test_team.id, 0)],
            'fold': True,
        })

        cls.tag_vip = cls.env['helpdesk.tag'].with_user(cls.helpdesk_manager).create({'name': 'VIP'})
        cls.tag_urgent = cls.env['helpdesk.tag'].with_user(cls.helpdesk_manager).create({'name': 'Urgent'})
        cls.tag_freeze = cls.env['helpdesk.tag'].with_user(cls.helpdesk_manager).create({'name': 'Freeze'})

        cls.sla = cls.env['helpdesk.sla'].create({
            'name': 'SLA',
            'team_id': cls.test_team.id,
            'time': 32,
            'stage_id': cls.stage_progress.id,
        })
        cls.sla_2 = cls.env['helpdesk.sla'].create({
            'name': 'SLA done stage with freeze time',
            'team_id': cls.test_team.id,
            'time': 10.033333333333333,
            'tag_ids': [(4, cls.tag_freeze.id)],
            'exclude_stage_ids': cls.stage_wait.ids,
            'stage_id': cls.stage_done.id,
        })

        # He also creates a ticket types for Question and Issue
        cls.type_question = cls.env['helpdesk.ticket.type'].with_user(cls.helpdesk_manager).create({
            'name': 'Question_test',
        }).sudo()
        cls.type_issue = cls.env['helpdesk.ticket.type'].with_user(cls.helpdesk_manager).create({
            'name': 'Issue_test',
        }).sudo()

    @contextmanager
    def _ticket_patch_now(self, datetime):
        with freeze_time(datetime), patch.object(self.env.cr, 'now', lambda: datetime):
            yield
            self.env.flush_all()

    def create_ticket(self, *arg, **kwargs):
        default_values = {
            'name': "Help me",
            'team_id': self.test_team.id,
            'tag_ids': [(4, self.tag_urgent.id)],
            'stage_id': self.stage_new.id,
            'priority': '1',
        }
        if 'tag_ids' in kwargs:
            # from recordset to ORM command
            kwargs['tag_ids'] = [(6, False, [tag.id for tag in kwargs['tag_ids']])]
        values = dict(default_values, **kwargs)
        return self.env['helpdesk.ticket'].create(values)

    def test_sla_no_tag(self):
        """ SLA without tag should apply to all tickets """
        self.sla.tag_ids = [(5,)]
        ticket = self.create_ticket(tag_ids=self.tag_urgent)
        self.assertEqual(ticket.sla_status_ids.sla_id, self.sla, "SLA should have been applied")

    def test_sla_single_tag(self):
        self.sla.tag_ids = [(4, self.tag_urgent.id)]
        ticket = self.create_ticket(tag_ids=self.tag_urgent)
        self.assertEqual(ticket.sla_status_ids.sla_id, self.sla, "SLA should have been applied")

    def test_sla_multiple_tags(self):
        self.sla.tag_ids = [(6, False, (self.tag_urgent | self.tag_vip).ids)]
        ticket = self.create_ticket(tag_ids=self.tag_urgent)
        self.assertEqual(ticket.sla_status_ids.sla_id, self.sla, "SLA should have been applied when atleast one tag set on ticket from sla policy")
        ticket.tag_ids = [(4, self.tag_vip.id)]
        self.assertEqual(ticket.sla_status_ids.sla_id, self.sla, "SLA should have been applied")

    def test_sla_tag_and_ticket_type(self):
        self.sla.tag_ids = [(6, False, self.tag_urgent.ids)]
        self.sla.ticket_type_ids = [Command.link(self.type_question.id)]
        ticket = self.create_ticket(tag_ids=self.tag_urgent)
        self.assertFalse(ticket.sla_status_ids, "SLA should not have been applied yet")
        ticket.ticket_type_id = self.type_question
        self.assertEqual(ticket.sla_status_ids.sla_id, self.sla, "SLA should have been applied")

    def test_sla_remove_tag(self):
        self.sla.tag_ids = [(6, False, (self.tag_urgent | self.tag_vip).ids)]
        ticket = self.create_ticket(tag_ids=self.tag_urgent | self.tag_vip)
        self.assertEqual(ticket.sla_status_ids.sla_id, self.sla, "SLA should have been applied")
        ticket.tag_ids = [(5,)]  # Remove all tags
        self.assertFalse(ticket.sla_status_ids, "SLA should no longer apply")

    def test_sla_waiting(self):
        with self._ticket_patch_now(NOW2):
            ticket = self.create_ticket(tag_ids=self.tag_freeze)
            status = ticket.sla_status_ids.filtered(lambda sla: sla.sla_id.id == self.sla_2.id)
            self.assertEqual(status.deadline, datetime(2019, 1, 9, 12, 2, 0), 'No waiting time, deadline = creation date + 1 day + 2 hours + 2 minutes')

        with self._ticket_patch_now('2019-01-08 11:09:50'):
            ticket.write({'stage_id': self.stage_progress.id})
            initial_values = {ticket.id: {'stage_id': self.stage_new}}
            ticket._message_track(['stage_id'], initial_values)
            self.assertEqual(status.deadline, datetime(2019, 1, 9, 12, 2, 0), 'No waiting time, deadline = creation date + 1 day + 2 hours + 2 minutes')

        # We are in waiting stage, they are no more deadline.
        with self._ticket_patch_now('2019-01-08 12:15:00'):
            ticket.write({'stage_id': self.stage_wait.id})
            initial_values = {ticket.id: {'stage_id': self.stage_progress}}
            ticket._message_track(['stage_id'], initial_values)
            self.assertFalse(status.deadline, 'In waiting stage: no more deadline')

        #  We have a response of our customer, the ticket switch to in progress stage (outside working hours)
        with self._ticket_patch_now('2019-01-12 10:35:58'):
            ticket.write({'stage_id': self.stage_progress.id})
            initial_values = {ticket.id: {'stage_id': self.stage_wait}}
            ticket._message_track(['stage_id'], initial_values)
            # waiting time = 3 full working days 9 - 10 - 11 January (12 doesn't count as it's Saturday)
            #  + (8 January) 12:15:00 -> 16:00:00 (end of working day) 3,75 hours
            # Old deadline = '2019-01-09 12:02:00'
            # New: '2019-01-09 12:02:00' + 3 days (waiting) + 2 days (weekend) + 3.75 hours (waiting) = '2019-01-14 15:47:00'
            self.assertEqual(status.deadline, datetime(2019, 1, 14, 15, 47), 'We have waiting time: deadline = old_deadline + 3 full working days (waiting) + 3.75 hours (waiting) + 2 days (weekend)')

        with self._ticket_patch_now('2019-01-14 15:30:00'):
            ticket.write({'stage_id': self.stage_wait.id})
            initial_values = {ticket.id: {'stage_id': self.stage_progress}}
            ticket._message_track(['stage_id'], initial_values)
            self.assertFalse(status.deadline, 'In waiting stage: no more deadline')

        # We need to patch now with a new value as it will be used to compute freezed time.
        with self._ticket_patch_now('2019-01-16 15:00:00'):
            ticket.write({'stage_id': self.stage_done.id})
            initial_values = {ticket.id: {'stage_id': self.stage_wait}}
            ticket._message_track(['stage_id'], initial_values)
            self.assertEqual(status.deadline, datetime(2019, 1, 16, 15, 17), 'We have waiting time: deadline = old_deadline +  7.5 hours (waiting)')

    def test_failed_tickets(self):
        with self._ticket_patch_now(NOW):
            self.sla.time = 3
            # Failed ticket
            self.create_ticket(user_id=self.env.user.id, create_date=NOW - relativedelta(hours=3, minutes=2))

            # Not failed ticket
            self.create_ticket(user_id=self.env.user.id, create_date=NOW - relativedelta(hours=2, minutes=2))

            data = self.env['helpdesk.team'].retrieve_dashboard()
            self.assertEqual(data['my_all']['count'], 2, "There should be 2 tickets")
            self.assertEqual(data['my_all']['failed'], 1, "There should be 1 failed ticket")

    def test_deadlines_after_work(self):
        with self._ticket_patch_now(NOW + relativedelta(hour=20, minute=0)):
            self.sla.time = 3
            # Set the calendar tz to UTC in order to ease test comprehension
            self.sla.company_id.resource_calendar_id.tz = 'UTC'
            ticket = self.create_ticket(user_id=self.env.user.id)
            # We set ticket create date to 20:00 which is out of the working calendar => The first possible time to work
            # on the ticket is the next day at 08:00
            self.assertEqual(ticket.sla_deadline, fields.Datetime.now() + relativedelta(days=1, hour=11), "Day0:20h + 3h = Day1:8h + 3h = Day1:11h")

            self.sla.time = 11
            ticket = self.create_ticket(user_id=self.env.user.id)
            self.assertEqual(ticket.sla_deadline, fields.Datetime.now() + relativedelta(days=2, hour=11), "Day0:20h + 11h = Day0:20h + 1day:3h = Day1:8h + 1day:3h = Day2:8h + 3h = Day2:11h")

    def test_deadlines_during_work(self):
        with self._ticket_patch_now(NOW + relativedelta(hour=8, minute=0)):
            self.sla.time = 3
            # Set the calendar tz to UTC in order to ease test comprehension
            self.sla.company_id.resource_calendar_id.tz = 'UTC'
            ticket = self.create_ticket(user_id=self.env.user.id)
            # We set ticket create date to 20:00 which is out of the working calendar => The first possible time to work
            # on the ticket is the next day at 08:00
            self.assertEqual(ticket.sla_deadline, fields.Datetime.now() + relativedelta(days=0, hour=11), "Day0:8h + 3h = Day0:11h")

            self.sla.time = 11
            ticket = self.create_ticket(user_id=self.env.user.id)
            self.assertEqual(ticket.sla_deadline, fields.Datetime.now() + relativedelta(days=1, hour=11), "Day0:8h + 11h = Day0:8h + 1day:3h = Day1:8h + 3h = Day1:11h")
