# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import Command
from odoo.addons.helpdesk.tests.common import HelpdeskCommon


class TestWebsiteHelpdeskLivechat(HelpdeskCommon):
    def setUp(self):
        super().setUp()

        self.livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'The channel',
            'user_ids': [Command.set([self.helpdesk_manager.id])]
        })

        user = self.helpdesk_manager
        self.patch(type(self.env['im_livechat.channel']), '_get_available_users', lambda _: user)

        self.test_team.use_website_helpdesk_livechat = True

    def test_helpdesk_commands(self):
        channel_info = self.livechat_channel.with_user(self.helpdesk_manager)._open_livechat_mail_channel(anonymous_name='Visitor')
        mail_channel = self.env['mail.channel'].browse(channel_info['id']).with_user(self.helpdesk_manager)

        self.assertFalse(self.env['helpdesk.ticket'].search([('team_id', '=', self.test_team.id)]), 'The team should start with no tickets')

        # Post a message that will be part of the chat history in the ticket description
        test_message = 'Test message'
        mail_channel.message_post(body=test_message)

        # Create the ticket with the /helpdesk command
        ticket_name = 'Test website helpdesk livechat'
        mail_channel.execute_command_helpdesk(body=f"/helpdesk {ticket_name}")

        bus = self.env['bus.bus'].search([('channel', 'like', f"\"res.partner\",{self.helpdesk_manager.partner_id.id}")], order='id desc', limit=1)
        message = json.loads(bus.message)
        ticket = self.env['helpdesk.ticket'].search([('team_id', '=', self.test_team.id)])
        expected_message = f"<span class='o_mail_notification'>Created a new ticket: <a href=# data-oe-model='helpdesk.ticket' data-oe-id='{ticket.id}'>{ticket_name} (#{ticket.id})</a></span>"

        self.assertTrue(ticket, f"Ticket {ticket_name} should have been created.")
        self.assertEqual(message['payload']['body'], expected_message, 'A message should be posted with a link to the created ticket.')
        self.assertIn(ticket_name, ticket.name, f"The created ticket should be named '{ticket_name}'.")
        self.assertIn(test_message, f"{self.helpdesk_manager.name}: {str(ticket.description)}", 'The chat history should be in the ticket description.')

        # Search the ticket with the /helpdesk_search command
        mail_channel.execute_command_helpdesk_search(body=f"/helpdesk_search {ticket_name}")

        bus = self.env['bus.bus'].search([('channel', 'like', f"\"res.partner\",{self.helpdesk_manager.partner_id.id}")], order='id desc', limit=1)
        message = json.loads(bus.message)
        expected_message = f"<span class='o_mail_notification'>We found some matched ticket(s) related to the search query: <br/><a href=# data-oe-model='helpdesk.ticket' data-oe-id='{ticket.id}'>{ticket_name} (#{ticket.id})</a></span>"

        self.assertEqual(message['payload']['body'], expected_message, 'A message should be posted saying the previously created ticket matches the command.')
