# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.fields import Datetime


class TestMACommon(TestMailFullCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMACommon, cls).setUpClass()

        cls.user_markauto = mail_new_test_user(
            cls.env, login='user_markauto',
            groups='base.group_user,base.group_partner_manager,marketing_automation.group_marketing_automation_user',
            name='Mounhir MarketAutoUser', signature='--\nM')
        cls.test_records = cls._create_marketauto_records(model='marketing.test.sms', count=2)

        cls.patcher = patch('odoo.addons.marketing_automation.models.marketing_campaign.Datetime', wraps=Datetime)
        cls.patcher2 = patch('odoo.addons.marketing_automation.models.marketing_activity.Datetime', wraps=Datetime)
        cls.patcher3 = patch('odoo.addons.marketing_automation.models.marketing_participant.Datetime', wraps=Datetime)
        cls.patcher4 = patch('odoo.addons.marketing_automation.models.marketing_trace.Datetime', wraps=Datetime)
        cls.patcher5 = patch('odoo.addons.marketing_automation_sms.models.marketing_activity.Datetime', wraps=Datetime)

        cls.mock_datetime = cls.startClassPatcher(cls.patcher)
        cls.mock_datetime2 = cls.startClassPatcher(cls.patcher2)
        cls.mock_datetime3 = cls.startClassPatcher(cls.patcher3)
        cls.mock_datetime4 = cls.startClassPatcher(cls.patcher4)
        cls.mock_datetime5 = cls.startClassPatcher(cls.patcher5)

    # ------------------------------------------------------------
    # TOOLS AND ASSERTS
    # ------------------------------------------------------------

    def assertMarketAutoTraces(self, participants_info, activity, **trace_values):
        """ Check content of traces.

        :param participants_info: [{
            # participants
            'records': records,                           # records going through this activity
            'status': status,                             # marketing trace status (processed, ...) for all records
            'participants': participants record_set,      # optional: allow to check coherency of expected participants
            # trace
            'schedule_date': datetime or False,           # optional: check schedule_date on marketing trace
            'trace_status': status of mailing trace,      # if not set: check there is no mailing trace
            'trace_content': content of mail/sms          # content of sent mail / sms
        }, {}, ... ]
        """
        all_records = self.env[activity.campaign_id.model_name]
        for info in participants_info:
            all_records += info['records']

        traces = self.env['marketing.trace'].search([
            ('activity_id', 'in', activity.ids),
        ])

        self.assertEqual(set(traces.mapped('res_id')), set(all_records.ids))
        for key, value in (trace_values or {}).items():
            self.assertEqual(set(traces.mapped(key)), set([value]))

        for info in participants_info:
            linked_traces = traces.filtered(lambda t: t.res_id in info['records'].ids)
            self.assertEqual(set(linked_traces.mapped('state')), set([info['status']]))
            self.assertEqual(set(linked_traces.mapped('res_id')), set(info['records'].ids))

            if 'schedule_date' in info:
                self.assertEqual(set(linked_traces.mapped('schedule_date')), set([info.get('schedule_date')]))

            if info.get('trace_status'):
                if activity.mass_mailing_id.mailing_type == 'mail':
                    self.assertMailTraces(
                        [{'partner': self.env['res.partner'],  # TDE FIXME: make it generic and check why partner seems unset
                          'email': record.email_normalized,  # TDE FIXME: make it generic and check for aprtner
                          'trace_status': info['trace_status'],
                          'failure_type': info.get('failure_type', False),
                          'record': record,
                         } for record in info['records']],
                        activity.mass_mailing_id,
                        info['records']
                    )
                else:
                    self.assertSMSTraces(
                        [{'partner': record.customer_id,  # TDE FIXME: make it generic
                          'number': record.phone_sanitized,  # TDE FIXME: make it generic
                          'trace_status': info['trace_status'],
                          'failure_type': info.get('failure_type', False),
                          'record': record,
                          'content': info.get('trace_content')
                         } for record in info['records']],
                        activity.mass_mailing_id,
                        info['records'],
                        sent_unlink=True
                    )
            else:
                self.assertEqual(linked_traces.mailing_trace_ids, self.env['mailing.trace'])
            if info.get('participants'):
                self.assertEqual(traces.participant_id, info['participants'])

    @classmethod
    def _set_mock_datetime_now(cls, datetime):
        cls.mock_datetime.now.return_value = datetime
        cls.mock_datetime2.now.return_value = datetime
        cls.mock_datetime3.now.return_value = datetime
        cls.mock_datetime4.now.return_value = datetime
        cls.mock_datetime5.now.return_value = datetime

    # ------------------------------------------------------------
    # RECORDS TOOLS
    # ------------------------------------------------------------

    @classmethod
    def _create_marketauto_records(cls, model='marketing.test.sms', count=1):
        """ Create records for marketing automation. Each batch consists in

          * 3 records with a valid partner w mobile and email;
          * 1 record without partner w email and mobile;
          * 1 record without partner, wo email and mobile
        """
        records = cls.env[model]
        for x in range(0, count):
            for inner_x in range(0, 5):
                current_idx = x * 5 + inner_x
                if inner_x < 3:
                    name = 'Customer_%02d' % (current_idx)
                    partner = cls.env['res.partner'].create({
                        'name': name,
                        'mobile': '045600%04d' % (current_idx),
                        'country_id': cls.env.ref('base.be').id,
                        'email': '"%s" <email_%02d@example.com>' % (name, current_idx),
                    })
                else:
                    partner = cls.env['res.partner']

                record_name = 'Test_%02d' % current_idx
                vals = {
                    'name': record_name,
                    'customer_id': partner.id,
                    'description': 'Linked to partner %s' % partner.name if partner else '',
                }
                if inner_x == 3:
                    vals['email_from'] = '"%s" <nopartner.email_%02d@example.com>' % (name, current_idx)
                    vals['mobile'] = '+3245600%04d' % (current_idx)

                records += records.create(vals)
        return records

    @classmethod
    def _create_mailing(cls, model='marketing.test.sms', **mailing_values):
        vals = {
            'name': 'SourceName',
            'subject': 'Test Subject',
            'mailing_type': 'mail',
            'body_html': '<div>Hello {{ object.name }}<br/>You rocks</div>',
            'mailing_model_id': cls.env['ir.model']._get(model).id,
            'use_in_marketing_automation': True,
        }
        vals.update(**mailing_values)
        return cls.env['mailing.mailing'].create(vals)

    @classmethod
    def _create_activity(cls, campaign, mailing=None, action=None, **act_values):
        vals = {
            'name': 'Activity %s' % (len(campaign.marketing_activity_ids) + 1),
            'campaign_id': campaign.id,
        }
        if mailing:
            if mailing.mailing_type == 'mail':
                vals.update({
                    'mass_mailing_id': mailing.id,
                    'activity_type': 'email',
                })
            else:
                vals.update({
                    'mass_mailing_id': mailing.id,
                    'activity_type': 'sms',
                })
        elif action:
            vals.update({
                'server_action_id': action.id,
                'activity_type': 'action',
            })
        vals.update(**act_values)
        return cls.env['marketing.activity'].create(vals)
