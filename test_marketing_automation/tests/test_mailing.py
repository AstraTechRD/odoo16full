# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMassMailing(CronMixinCase, TestMACommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailing, cls).setUpClass()

        cls.test_records2 = cls.env['res.partner'].create([{
            'name': 'test1',
            'email': 'test1@test.com',
        }, {
            'name': 'test1-duplicate',
            'email': 'test1@test.com',
        }, {
            'name': 'test2',
            'email': 'test2@test.com',
        }])

    def test_duplicate_is_test(self):
        """ Check that only non-tests records can be considered as duplicates"""
        mailing = self.env['mailing.mailing'].create({
            'name': 'Great Mailing',
            'subject': 'Test Subject',
            'mailing_type': 'mail',
            'body_html': '<div>Hey {{ object.name }}<br/>YOU rock</div>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'use_in_marketing_automation': True,
        })
        campaign = self.env['marketing.campaign'].create({
            'name': 'Great Campaign',
            'domain': f"{[('id', 'in', self.test_records2.ids)]}",
        })
        activity = self.env['marketing.activity'].create({
            'name': 'Greater Activity',
            'campaign_id': campaign.id,
            'mass_mailing_id': mailing.id,
            'activity_type': 'email',
        })
        test_participant_1 = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'res_id': self.test_records2[0],
            'is_test': True,
        })
        test_participant_2 = self.env['marketing.participant'].create({
            'campaign_id': campaign.id,
            'res_id': self.test_records2[0],
            'is_test': True,
        })
        # test campaign flow: we want to make sure that when creating multiple test campaigns with the same customer
        # the customer will still receive multiple mails (not considered as duplicate)
        self.env['marketing.campaign.test'].create({
            'campaign_id': campaign.id,
            'res_id': self.test_records2[0].id,
        })
        trace_test_1 = self.env['marketing.trace'].search([('participant_id', '=', test_participant_1.id)])
        with self.mock_mail_gateway(mail_unlink_sent=False):
            trace_test_1.action_execute()
        self.assertEqual(len(self._mails), 1)

        self.env['marketing.campaign.test'].create({
            'campaign_id': campaign.id,
            'res_id': self.test_records2[0].id,
        })
        trace_test_2 = self.env['marketing.trace'].search([('participant_id', '=', test_participant_2.id)])
        trace_test_2.flush_model(['is_test'])
        with self.mock_mail_gateway(mail_unlink_sent=False):
            trace_test_2.action_execute()
        self.assertEqual(len(self._mails), 1, 'test1 should have received an email')

        # normal campaign flow
        campaign.action_start_campaign()
        self.assertEqual(campaign.state, 'running')
        campaign.sync_participants()
        self.assertEqual(
            activity.trace_ids.mapped('participant_id'),
            campaign.participant_ids,
        )
        with self.mock_mail_gateway(mail_unlink_sent=False):
            activity.execute_on_traces(activity.trace_ids)
        self.assertEqual(len(self._mails), 2, 'Should have sent 2 emails.')
