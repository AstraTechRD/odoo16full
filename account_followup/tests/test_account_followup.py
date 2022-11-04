# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountFollowupReports(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env['account_followup.followup.line'].search([]).unlink()

        cls.first_followup_line = cls.env['account_followup.followup.line'].create({
            'name': 'first_followup_line',
            'delay': -10,
            'send_email': False,
            'company_id': cls.company_data['company'].id
        })
        cls.second_followup_line = cls.env['account_followup.followup.line'].create({
            'name': 'second_followup_line',
            'delay': 10,
            'send_email': False,
            'company_id': cls.company_data['company'].id
        })
        cls.third_followup_line = cls.env['account_followup.followup.line'].create({
            'name': 'third_followup_line',
            'delay': 15,
            'send_email': False,
            'company_id': cls.company_data['company'].id
        })

    def assertPartnerFollowup(self, partner, status, line):
        partner.invalidate_recordset(['followup_status', 'followup_line_id'])
        res = partner._query_followup_data()
        self.assertEqual(res.get(partner.id, {}).get('followup_status'), status)
        self.assertEqual(res.get(partner.id, {}).get('followup_line_id'), line.id if line else None)
        self.assertEqual(partner.followup_status, status or 'no_action_needed')
        self.assertEqual(partner.followup_line_id.id if partner.followup_line_id else None, line.id if line else None)

    def test_followup_responsible(self):
        """
        Test that the responsible is correctly set
        """
        user1 = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
            'groups_id': [(6, 0, [self.env.ref('account.group_account_user').id])]
        })
        user2 = self.env['res.users'].create({
            'name': 'Another User',
            'login': 'another_user',
            'email': 'another@user.com',
            'groups_id': [(6, 0, [self.env.ref('account.group_account_user').id])]
        })
        # 1- no info, use current user
        self.assertEqual(self.partner_a._get_followup_responsible(), self.env.user)

        # 2- set invoice user
        invoice1 = self.init_invoice('out_invoice', partner=self.partner_a,
                                     invoice_date=fields.Date.from_string('2000-01-01'),
                                     amounts=[2000])
        invoice2 = self.init_invoice('out_invoice', partner=self.partner_a,
                                     invoice_date=fields.Date.from_string('2000-01-01'),
                                     amounts=[1000])
        invoice1.invoice_user_id = user1
        invoice2.invoice_user_id = user2
        (invoice1 + invoice2).action_post()
        # Should pick invoice_user_id of the most delayed move, with highest residual amount in case of tie (invoice1)
        self.assertEqual(self.partner_a._get_followup_responsible(), user1)

        self.partner_a.followup_line_id = self.first_followup_line

        # 3- A followup responsible user has been set on the partner
        self.partner_a.followup_responsible_id = user2
        self.assertEqual(self.partner_a._get_followup_responsible(), user2)

        # 4- Modify the default responsible on followup level
        self.partner_a.followup_line_id.activity_default_responsible_type = 'salesperson'
        self.assertEqual(self.partner_a._get_followup_responsible(), user1)

        self.partner_a.followup_line_id.activity_default_responsible_type = 'account_manager'
        self.partner_a.user_id = user2
        self.assertEqual(self.partner_a._get_followup_responsible(), self.partner_a.user_id)

    def test_followup_line_and_status(self):
        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-01-02',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice_1.action_post()

        with freeze_time('2021-12-20'):
            # Today < due date + delay first followup level (negative delay -> reminder before due date)
            self.assertPartnerFollowup(self.partner_a, 'no_action_needed', None)

        with freeze_time('2021-12-24'):
            # Today = due date + delay first followup level
            self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', self.first_followup_line)

            # followup_next_action_date not exceeded but no invoice is overdue,
            # we should not be in status 'with_overdue_invoices' but 'no action needed'
            self.partner_a.followup_next_action_date = fields.Date.from_string('2021-12-25')
            self.assertPartnerFollowup(self.partner_a, 'no_action_needed', self.first_followup_line)

        with freeze_time('2022-01-13'):
            # Today > due date + delay second followup level but first followup level not processed yet
            self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', self.first_followup_line)

            self.partner_a._execute_followup_partner()
            # Due date exceeded but first followup level processed
            # followup_next_action_date set in 20 days (delay 2nd level - delay 1st level = 10 - (-10) = 20)
            self.assertPartnerFollowup(self.partner_a, 'with_overdue_invoices', self.second_followup_line)
            self.assertEqual(self.partner_a.followup_next_action_date, fields.Date.from_string('2022-02-02'))

        with freeze_time('2022-02-03'):
            # followup_next_action_date exceeded and invoice not reconciled yet
            self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', self.second_followup_line)

            # Exclude every unreconciled invoice lines
            for aml in self.partner_a.unreconciled_aml_ids:
                aml.blocked = True
            # Every unreconciled invoice lines are blocked, the result from the query will be None
            self.assertPartnerFollowup(self.partner_a, None, None)

    def test_followup_contacts(self):
        followup_contacts = self.partner_a._get_all_followup_contacts()
        self.assertEqual(self.env['res.partner'], followup_contacts)

        followup_partner_1 = self.env['res.partner'].create({
            'name': 'followup partner 1',
            'parent_id': self.partner_a.id,
            'type': 'followup',
        })
        followup_partner_2 = self.env['res.partner'].create({
            'name': 'followup partner 2',
            'parent_id': self.partner_a.id,
            'type': 'followup',
        })
        expected_partners = followup_partner_1 + followup_partner_2
        followup_contacts = self.partner_a._get_all_followup_contacts()
        self.assertEqual(expected_partners, followup_contacts)
