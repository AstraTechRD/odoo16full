# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading

from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.fields import Datetime
from odoo.exceptions import ValidationError


class MarketingCampaign(models.Model):
    _name = 'marketing.campaign'
    _description = 'Marketing Campaign'
    _inherits = {'utm.campaign': 'utm_campaign_id'}
    _order = 'create_date DESC'

    utm_campaign_id = fields.Many2one('utm.campaign', 'UTM Campaign', ondelete='restrict', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('running', 'Running'),
        ('stopped', 'Stopped')
        ], copy=False, default='draft',
        group_expand='_group_expand_states')
    model_id = fields.Many2one(
        'ir.model', string='Model', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.ref('base.model_res_partner', raise_if_not_found=False),
        domain="['&', ('is_mail_thread', '=', True), ('model', '!=', 'mail.blacklist')]")
    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)
    unique_field_id = fields.Many2one(
        'ir.model.fields', string='Unique Field',
        compute='_compute_unique_field_id', readonly=False, store=True,
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['char', 'int', 'many2one', 'text', 'selection'])]",
        help="""Used to avoid duplicates based on model field.\ne.g.
                For model 'Customers', select email field here if you don't
                want to process records which have the same email address""")
    domain = fields.Char(string="Filter", compute='_compute_domain', readonly=False, store=True)
    # Mailing Filter
    mailing_filter_id = fields.Many2one(
        'mailing.filter', string='Favorite Filter',
        domain="[('mailing_model_name', '=', model_name)]",
        compute='_compute_mailing_filter_id', readonly=False, store=True)
    mailing_filter_domain = fields.Char('Favorite filter domain', related='mailing_filter_id.mailing_domain')
    mailing_filter_count = fields.Integer('# Favorite Filters', compute='_compute_mailing_filter_count')
    # activities
    marketing_activity_ids = fields.One2many('marketing.activity', 'campaign_id', string='Activities', copy=False)
    mass_mailing_count = fields.Integer('# Mailings', compute='_compute_mass_mailing_count')
    link_tracker_click_count = fields.Integer('# Clicks', compute='_compute_link_tracker_click_count')
    last_sync_date = fields.Datetime(string='Last activities synchronization')
    require_sync = fields.Boolean(string="Sync of participants is required", compute='_compute_require_sync')
    # participants
    participant_ids = fields.One2many('marketing.participant', 'campaign_id', string='Participants', copy=False)
    running_participant_count = fields.Integer(string="# of active participants", compute='_compute_participants')
    completed_participant_count = fields.Integer(string="# of completed participants", compute='_compute_participants')
    total_participant_count = fields.Integer(string="# of active and completed participants", compute='_compute_participants')
    test_participant_count = fields.Integer(string="# of test participants", compute='_compute_participants')

    @api.constrains('model_id', 'mailing_filter_id')
    def _check_mailing_filter_model(self):
        """Check that if the favorite filter is set, it must contain the same target model as campaign"""
        for campaign in self:
            if campaign.mailing_filter_id and campaign.model_id != campaign.mailing_filter_id.mailing_model_id:
                raise ValidationError(
                    _("The saved filter targets different model and is incompatible with this campaign.")
                )

    @api.depends('model_id')
    def _compute_unique_field_id(self):
        for campaign in self:
            campaign.unique_field_id = False

    @api.depends('model_id', 'mailing_filter_id')
    def _compute_domain(self):
        for campaign in self:
            if campaign.mailing_filter_id:
                campaign.domain = campaign.mailing_filter_id.mailing_domain
            else:
                campaign.domain = repr([])

    @api.depends('marketing_activity_ids.require_sync', 'last_sync_date')
    def _compute_require_sync(self):
        for campaign in self:
            if campaign.last_sync_date and campaign.state == 'running':
                activities_changed = campaign.marketing_activity_ids.filtered(lambda activity: activity.require_sync)
                campaign.require_sync = bool(activities_changed)
            else:
                campaign.require_sync = False

    @api.depends('model_id', 'domain')
    def _compute_mailing_filter_count(self):
        filter_data = self.env['mailing.filter']._read_group([
            ('mailing_model_id', 'in', self.model_id.ids)
        ], ['mailing_model_id'], ['mailing_model_id'])
        mapped_data = {data['mailing_model_id'][0]: data['mailing_model_id_count'] for data in filter_data}
        for campaign in self:
            campaign.mailing_filter_count = mapped_data.get(campaign.model_id.id, 0)

    @api.depends('model_name')
    def _compute_mailing_filter_id(self):
        for mailing in self:
            mailing.mailing_filter_id = False

    @api.depends('marketing_activity_ids.mass_mailing_id')
    def _compute_mass_mailing_count(self):
        # TDE NOTE: this could be optimized but is currently displayed only in a form view, no need to optimize now
        for campaign in self:
            campaign.mass_mailing_count = len(campaign.mapped('marketing_activity_ids.mass_mailing_id').filtered(lambda mailing: mailing.mailing_type == 'mail'))

    @api.depends('marketing_activity_ids.mass_mailing_id')
    def _compute_link_tracker_click_count(self):
        click_data = self.env['link.tracker.click'].sudo().read_group(
            [('mass_mailing_id', 'in', self.mapped('marketing_activity_ids.mass_mailing_id').ids)],
            ['mass_mailing_id', 'ip'],
            ['mass_mailing_id']
        )
        mapped_data = {data['mass_mailing_id'][0]: data['mass_mailing_id_count'] for data in click_data}
        for campaign in self:
            campaign.link_tracker_click_count = sum(mapped_data.get(mailing_id, 0)
                                                    for mailing_id in campaign.mapped('marketing_activity_ids.mass_mailing_id').ids)

    @api.depends('participant_ids.state')
    def _compute_participants(self):
        participants_data = self.env['marketing.participant'].read_group(
            [('campaign_id', 'in', self.ids)],
            ['campaign_id', 'state', 'is_test'],
            ['campaign_id', 'state', 'is_test'], lazy=False)
        mapped_data = {campaign.id: {'is_test': 0} for campaign in self}
        for data in participants_data:
            if data['is_test']:
                mapped_data[data['campaign_id'][0]]['is_test'] += data['__count']
            else:
                mapped_data[data['campaign_id'][0]][data['state']] = data['__count']
        for campaign in self:
            campaign_data = mapped_data.get(campaign.id)
            campaign.running_participant_count = campaign_data.get('running', 0)
            campaign.completed_participant_count = campaign_data.get('completed', 0)
            campaign.total_participant_count = campaign.completed_participant_count + campaign.running_participant_count
            campaign.test_participant_count = campaign_data.get('is_test')

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """ Copy the activities of the campaign, each parent_id of each child
        activities should be set to the new copied parent activity. """
        new_compaign = super(MarketingCampaign, self).copy(dict(default or {}))

        old_to_new = {}

        for marketing_activity_id in self.marketing_activity_ids:
            new_marketing_activity_id = marketing_activity_id.copy()
            old_to_new[marketing_activity_id] = new_marketing_activity_id
            new_marketing_activity_id.write({
                'campaign_id': new_compaign.id,
                'require_sync': False,
                'trace_ids': False,
            })

        for marketing_activity_id in new_compaign.marketing_activity_ids:
            marketing_activity_id.parent_id = old_to_new.get(
                marketing_activity_id.parent_id)

        return new_compaign

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update({'is_auto_campaign': True})
        return super(MarketingCampaign, self).create(vals_list)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if any(campaign.marketing_activity_ids for campaign in self):
            return {'warning': {
                'title': _("Warning"),
                'message': _("Switching Target Model invalidates the existing activities. "
                             "Either update your activity actions to match the new Target Model or delete them.")
            }}

    def action_set_synchronized(self):
        self.write({'last_sync_date': Datetime.now()})
        self.mapped('marketing_activity_ids').write({'require_sync': False})

    def action_update_participants(self):
        """ Synchronizes all participants based campaign activities demanding synchronization
        It is done in 2 part:

         * update traces related to updated activities. This means basically recomputing the
           schedule date
         * creating new traces for activities recently added in the workflow :

          * 'begin' activities simple create new traces for all running participants;
          * other activities: create child for traces linked to the parent of the newly created activity
          * we consider scheduling to be done after parent processing, independently of other time considerations
          * for 'not' triggers take into account brother traces that could be already processed
        """
        for campaign in self:
            # Action 1: On activity modification
            modified_activities = campaign.marketing_activity_ids.filtered(lambda activity: activity.require_sync)
            traces_to_reschedule = self.env['marketing.trace'].search([
                ('state', '=', 'scheduled'),
                ('activity_id', 'in', modified_activities.ids)])
            for trace in traces_to_reschedule:
                trace_offset = relativedelta(**{trace.activity_id.interval_type: trace.activity_id.interval_number})
                trigger_type = trace.activity_id.trigger_type
                if trigger_type == 'begin':
                    trace.schedule_date = Datetime.from_string(trace.participant_id.create_date) + trace_offset
                elif trigger_type in ['activity', 'mail_not_open', 'mail_not_click', 'mail_not_reply'] and trace.parent_id:
                    trace.schedule_date = Datetime.from_string(trace.parent_id.schedule_date) + trace_offset
                elif trace.parent_id:
                    process_dt = trace.parent_id.mailing_trace_ids.state_update
                    trace.schedule_date = Datetime.from_string(process_dt) + trace_offset

            # Action 2: On activity creation
            created_activities = campaign.marketing_activity_ids.filtered(lambda a: a.create_date >= campaign.last_sync_date)
            for activity in created_activities:
                activity_offset = relativedelta(**{activity.interval_type: activity.interval_number})
                # Case 1: Trigger = begin
                # Create new root traces for all running participants -> consider campaign begin date is now to avoid spamming participants
                if activity.trigger_type == 'begin':
                    participants = self.env['marketing.participant'].search([
                        ('state', '=', 'running'), ('campaign_id', '=', campaign.id)
                    ])
                    for participant in participants:
                        schedule_date = Datetime.from_string(Datetime.now()) + activity_offset
                        self.env['marketing.trace'].create({
                            'activity_id': activity.id,
                            'participant_id': participant.id,
                            'schedule_date': schedule_date,
                        })
                else:
                    valid_parent_traces = self.env['marketing.trace'].search([
                        ('state', '=', 'processed'),
                        ('activity_id', '=', activity.parent_id.id)
                    ])

                    # avoid creating new traces that would have processed brother traces already processed
                    # example: do not create a mail_not_click trace if mail_click is already processed
                    if activity.trigger_type in ['mail_not_open', 'mail_not_click', 'mail_not_reply']:
                        opposite_trigger = activity.trigger_type.replace('_not_', '_')
                        brother_traces = self.env['marketing.trace'].search([
                            ('parent_id', 'in', valid_parent_traces.ids),
                            ('trigger_type', '=', opposite_trigger),
                            ('state', '=', 'processed'),
                        ])
                        valid_parent_traces = valid_parent_traces - brother_traces.mapped('parent_id')

                    valid_parent_traces.mapped('participant_id').filtered(lambda participant: participant.state == 'completed').action_set_running()

                    for parent_trace in valid_parent_traces:
                        self.env['marketing.trace'].create({
                            'activity_id': activity.id,
                            'participant_id': parent_trace.participant_id.id,
                            'parent_id': parent_trace.id,
                            'schedule_date': Datetime.from_string(parent_trace.schedule_date) + activity_offset,
                        })

        self.action_set_synchronized()

    def action_start_campaign(self):
        if any(not campaign.marketing_activity_ids for campaign in self):
            raise ValidationError(_('You must set up at least one activity to start this campaign.'))

        # trigger CRON job ASAP so that participants are synced
        cron = self.env.ref('marketing_automation.ir_cron_campaign_sync_participants')
        cron._trigger(at=Datetime.now())
        self.write({'state': 'running'})

    def action_stop_campaign(self):
        self.write({'state': 'stopped'})

    def action_view_mailings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.mail_mass_mailing_action_marketing_automation")
        action['domain'] = [
            '&',
            ('use_in_marketing_automation', '=', True),
            ('id', 'in', self.mapped('marketing_activity_ids.mass_mailing_id').ids),
            ('mailing_type', '=', 'mail')
        ]
        action['context'] = dict(self.env.context)
        action['context'].update({
            # defaults
            'default_mailing_model_id': self.model_id.id,
            'default_campaign_id': self.utm_campaign_id.id,
            'default_use_in_marketing_automation': True,
            'default_mailing_type': 'mail',
            'default_state': 'done',
            # action
            'create': False,
        })
        return action

    def action_view_tracker_statistics(self):
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.link_tracker_action_marketing_campaign")
        action['domain'] = [
            ('mass_mailing_id', 'in', self.mapped('marketing_activity_ids.mass_mailing_id').ids)
        ]
        return action

    def sync_participants(self):
        """ Creates new participants, taking into account already-existing ones
        as well as campaign filter and unique field. """
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        participants = self.env['marketing.participant']
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        for campaign in self.filtered(lambda c: c.marketing_activity_ids):
            now = Datetime.now()
            if not campaign.last_sync_date:
                campaign.last_sync_date = now

            RecordModel = self.env[campaign.model_name]

            # Fetch existing participants
            participants_data = participants.search_read([('campaign_id', '=', campaign.id)], ['res_id'])
            existing_rec_ids = _uniquify_list([live_participant['res_id'] for live_participant in participants_data])

            record_domain = literal_eval(campaign.domain or "[]")
            db_rec_ids = _uniquify_list(RecordModel.search(record_domain).ids)
            to_create = [rid for rid in db_rec_ids if rid not in existing_rec_ids]  # keep ordered IDs
            to_remove = set(existing_rec_ids) - set(db_rec_ids)
            unique_field = campaign.unique_field_id.sudo()
            if unique_field.name != 'id':
                without_duplicates = []
                existing_records = RecordModel.with_context(prefetch_fields=False).browse(existing_rec_ids).exists()
                # Split the read in batch of 1000 to avoid the prefetch
                # crawling the cache for the next 1000 records to fetch
                unique_field_vals = {rec[unique_field.name]
                                        for index in range(0, len(existing_records), 1000)
                                        for rec in existing_records[index:index+1000]}

                for rec in RecordModel.with_context(prefetch_fields=False).browse(to_create):
                    field_val = rec[unique_field.name]
                    # we exclude the empty recordset with the first condition
                    if (not unique_field.relation or field_val) and field_val not in unique_field_vals:
                        without_duplicates.append(rec.id)
                        unique_field_vals.add(field_val)
                to_create = without_duplicates

            BATCH_SIZE = 100
            for to_create_batch in tools.split_every(BATCH_SIZE, to_create, piece_maker=list):
                participants |= participants.create([{
                    'campaign_id': campaign.id,
                    'res_id': rec_id,
                } for rec_id in to_create_batch])

                if auto_commit:
                    self.env.cr.commit()

            if to_remove:
                participants_to_unlink = participants.search([
                    ('res_id', 'in', list(to_remove)),
                    ('campaign_id', '=', campaign.id),
                    ('state', '!=', 'unlinked'),
                ])
                for index in range(0, len(participants_to_unlink), 1000):
                    participants_to_unlink[index:index+1000].action_set_unlink()
                    # Commit only every 100 operation to avoid committing to often
                    # this mean every 10k record. It should be ok, it takes 1sec second to process 10k
                    if not index % (BATCH_SIZE * 100):
                        self.env.cr.commit()

        return participants

    def execute_activities(self):
        for campaign in self:
            campaign.marketing_activity_ids.execute()
