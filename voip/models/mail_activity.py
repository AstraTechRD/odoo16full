# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    phone = fields.Char('Phone', compute='_compute_phone_numbers', readonly=False, store=True)
    mobile = fields.Char('Mobile', compute='_compute_phone_numbers', readonly=False, store=True)
    voip_phonecall_id = fields.Many2one('voip.phonecall', 'Linked Voip Phonecall')

    @api.depends('res_model', 'res_id', 'activity_type_id')
    def _compute_phone_numbers(self):
        phonecall_activities = self.filtered(
            lambda act: act.id and act.res_model and act.res_id and act.activity_category == 'phonecall'
        )
        (self - phonecall_activities).phone = False
        (self - phonecall_activities).mobile = False

        if phonecall_activities:
            voip_info = phonecall_activities._get_customer_phone_info()
            for activity in phonecall_activities:
                activity.mobile = voip_info[activity.id]['mobile']
                activity.phone = voip_info[activity.id]['phone']

    @api.model_create_multi
    def create(self, values_list):
        activities = super(MailActivity, self).create(values_list)

        phonecall_activities = activities.filtered(
            lambda act: (act.phone or act.mobile) and act.activity_category == 'phonecall'
        )
        if phonecall_activities:
            # avoid clash with default_type
            phonecalls = self.env['voip.phonecall'].with_context(
                tools.clean_context(self.env.context)
            ).create(
                phonecall_activities._prepare_voip_phonecall_values_list()
            )
            for activity, phonecall in zip(phonecall_activities, phonecalls):
                activity.voip_phonecall_id = phonecall.id

            users_to_notify = phonecall_activities.user_id
            if users_to_notify:
                self.env['bus.bus']._sendmany([
                    [user.partner_id, 'refresh_voip', {}]
                    for user in users_to_notify
                ])
        return activities

    def write(self, values):
        if 'date_deadline' in values:
            self.voip_phonecall_id.date_deadline = values['date_deadline']
            if self.user_id:
                self.env['bus.bus']._sendmany([
                    [partner, 'refresh_voip', {}]
                    for partner in self.user_id.partner_id
                ])
        return super(MailActivity, self).write(values)

    def _get_customer_phone_info(self):
        """ Batch compute customer as well as mobile / phone information used
        to fill activities fields. This is used notably by voip to create
        phonecalls.

        :return dict: for each activity ID, get an information dict containing
          * partner: a res.partner record (maybe void) that is the customer
            related to the activity record;
          * mobile: mobile number (coming from activity record or partner);
          * phone: phone numbe (coming from activity record or partner);
        """
        activity_voip_info = {}
        data_by_model = self._classify_by_model()

        for model, data in data_by_model.items():
            records = self.env[model].browse(data['record_ids'])
            for record, activity in zip(records, data['activities']):
                customer = self.env['res.partner']
                mobile = record.mobile if 'mobile' in record else False
                phone = record.phone if 'phone' in record else False
                if not phone and not mobile:
                    # take only the first found partner if multiple customers are
                    # related to the record; anyway we will create only one phonecall
                    if hasattr(record, '_mail_get_partner_fields'):
                        customer = next(
                            (partner
                             for partner in record._mail_get_partners()[record.id]
                             if partner and (partner.phone or partner.mobile)),
                            self.env['res.partner']
                        )
                    else:
                        # find relational fields linking to partners if model does not
                        # inherit from mail.thread, just to have a fallback
                        partner_fnames = [
                            fname for fname, fvalue in records._fields.items()
                            if fvalue.type == 'many2one' and fvalue.comodel_name == 'res.partner'
                        ]
                        customer = next(
                            (record[fname] for fname in partner_fnames
                             if record[fname] and (record[fname].phone or record[fname].mobile)),
                            self.env['res.partner']
                        )
                    phone = customer.phone
                    mobile = customer.mobile
                activity_voip_info[activity.id] = {
                    'mobile': mobile,
                    'partner': customer,
                    'phone': phone,
                }
        return activity_voip_info

    def _prepare_voip_phonecall_values_list(self):
        voip_info = self._get_customer_phone_info()
        return [{
            'activity_id': activity.id,
            'date_deadline': activity.date_deadline,
            'name': activity.res_name,
            'mobile': activity.mobile,
            'partner_id': voip_info[activity.id]['partner'].id,
            'phone': activity.phone,
            'user_id': activity.user_id.id,
            'note': activity.note,
            'state': 'open',
        } for activity in self]

    def _action_done(self, feedback=False, attachment_ids=None):
        # extract potential required data to update phonecalls
        now = fields.Datetime.now()
        phonecall_values_list = [
            {
                'call_date': activity.voip_phonecall_id.call_date,
                'note': activity.note,
                'partner_id': activity.user_id.partner_id.id,
                'voip_phonecall_id': activity.voip_phonecall_id,
            } if activity.voip_phonecall_id else {}
            for activity in self
        ]

        # call super, and unlink `self`
        messages, activities = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

        # update phonecalls and broadcast refresh notifications on bus
        pids_to_notify = set()
        for phonecall_values, message in zip(phonecall_values_list, messages):
            if not phonecall_values:
                continue
            values_to_write = {
                'call_date': phonecall_values['call_date'] or now,
                'mail_message_id': message.id,
                'state': 'done',
                'note': feedback if feedback else phonecall_values['note'],
            }
            phonecall_values['voip_phonecall_id'].write(values_to_write)
            if phonecall_values['partner_id']:
                pids_to_notify.add(phonecall_values['partner_id'])

        if pids_to_notify:
            self.env['bus.bus']._sendmany([
                [partner, 'refresh_voip', {}]
                for partner in self.env['res.partner'].browse(list(pids_to_notify))
            ])

        return messages, activities
