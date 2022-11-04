# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from markupsafe import Markup

from odoo import api, fields, models, _


class VoipPhonecall(models.Model):
    _name = "voip.phonecall"
    _description = 'VOIP Phonecall'

    _order = "sequence, id"

    name = fields.Char('Call Name', required=True)
    date_deadline = fields.Date('Due Date', default=lambda self: fields.Date.today())
    call_date = fields.Datetime('Call Date')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.uid)
    partner_id = fields.Many2one('res.partner', 'Contact')
    activity_id = fields.Many2one('mail.activity', 'Linked Activity')
    mail_message_id = fields.Many2one('mail.message', 'Linked Chatter Message', index=True)
    note = fields.Html('Note')
    duration = fields.Float('Duration', help="Duration in minutes.")
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile')
    in_queue = fields.Boolean('In Call Queue', default=True)
    sequence = fields.Integer('Sequence', index=True,
        help="Gives the sequence order when displaying a list of Phonecalls.")
    start_time = fields.Integer("Start time")
    state = fields.Selection([
        ('pending', 'Not Held'),
        ('cancel', 'Cancelled'),
        ('open', 'To Do'),
        ('done', 'Held'),
        ('rejected', 'Rejected'),
        ('missed',   'Missed')
    ], string='Status', default='open',
        help='The status is set to To Do, when a call is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the call is not applicable anymore, the status can be set to Cancelled.')
    direction = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing')
    ], default='outgoing')

    def init_call(self):
        self.ensure_one()
        self.call_date = fields.Datetime.now()
        self.start_time = int(time.time())

    def hangup_call(self, duration_seconds=0, done=True):
        self.ensure_one()
        duration_minutes = round(duration_seconds / 60, 2)
        if done:
            note = False
            if self.activity_id:
                note = self.activity_id.note
                minutes = int(duration_minutes)
                seconds = int(duration_seconds - minutes * 60)
                duration_log = Markup('<br/><p>%s</p>') % _('Call duration: %(min)smin %(sec)ssec', min=minutes, sec=seconds)
                if self.activity_id.note:
                    self.activity_id.note += duration_log
                else:
                    self.activity_id.note = duration_log
                self.activity_id.action_done()
            self.write({
                'state': 'done',
                'duration': duration_minutes,
                'note': note,
            })
        else:
            self.write({
                'duration': duration_minutes,
            })
        return

    def canceled_call(self):
        self.ensure_one()
        self.state = "pending"

    def remove_from_queue(self):
        self.ensure_one()
        self.in_queue = False
        res_id = self.activity_id.res_id
        if(self.activity_id and self.state in ['pending', 'open']):
            self.state = 'cancel'
            self.activity_id.unlink()
        return res_id

    def _get_info(self):
        infos = []
        for record in self:
            info = {
                'id': record.id,
                'name': record.name,
                'state': record.state,
                'date_deadline': record.date_deadline,
                'call_date': record.call_date,
                'duration': record.duration,
                'phone': record.phone,
                'mobile': record.mobile,
                'note': record.note,
            }
            if record.partner_id:
                ir_model = record.env['ir.model']._get('res.partner')
                info.update({
                    'partner_id': record.partner_id.id,
                    'activity_res_id': record.partner_id.id,
                    'activity_res_model': 'res.partner',
                    'activity_model_name': ir_model.display_name,
                    'partner_name': record.partner_id.name,
                    'partner_avatar_128': record.partner_id.avatar_128,
                    'partner_email': record.partner_id.email
                })
            if record.activity_id:
                ir_model = record.env['ir.model']._get(record.activity_id.res_model)
                info.update({
                    'activity_id': record.activity_id.id,
                    'activity_res_id': record.activity_id.res_id,
                    'activity_res_model': record.activity_id.res_model,
                    'activity_model_name': ir_model.display_name,
                    'activity_summary': record.activity_id.summary,
                    'activity_note': record.activity_id.note
                })
            elif record.mail_message_id:
                ir_model = record.env['ir.model']._get(record.mail_message_id.model)
                info.update({
                    'activity_res_id': record.mail_message_id.res_id,
                    'activity_res_model': record.mail_message_id.model,
                    'activity_model_name': ir_model.display_name
                })
            infos.append(info)
        return infos

    @api.model
    def get_next_activities_list(self):
        return self.search([
            '|',
            ('activity_id', '!=', False),
            ('mail_message_id', '!=', False),
            ('in_queue', '=', True),
            ('user_id', '=', self.env.user.id),
            ('date_deadline', '<=', fields.Date.today()),
            ('state', '!=', 'done')
        ], order='sequence,date_deadline,id')._get_info()

    @api.model
    def get_recent_list(self, search_expr=None, offset=0, limit=None):
        domain = [
            ('user_id', '=', self.env.user.id),
            ('call_date', '!=', False),
            ('in_queue', '=', True),
        ]
        if search_expr:
            domain += [['name', 'ilike', search_expr]]
        return self.search(domain, offset=offset, limit=limit, order='call_date desc')._get_info()

    @api.model
    def get_missed_call_info(self):
        domain = [
            ('user_id', '=', self.env.user.id),
            ('call_date', '!=', False),
            ('in_queue', '=', True),
            ('state', '=', 'missed'),
        ]
        last_seen_phone_call = self.env.user.last_seen_phone_call
        if last_seen_phone_call:
            domain += [('id', '>', last_seen_phone_call.id)]
        return (self.search_count(domain), last_seen_phone_call.call_date)

    @api.model
    def _create_and_init(self, vals):
        phonecall = self.create(vals)
        phonecall.init_call()
        return phonecall._get_info()[0]

    def _update_and_init(self, vals):
        self.ensure_one()
        self.update(vals)
        return self._get_info()[0]

    @api.model
    def create_from_contact(self, partner_id):
        partner = self.env['res.partner'].browse(partner_id)
        vals = {
            'name': partner.name,
            'phone': partner.sanitized_phone,
            'mobile': partner.sanitized_mobile,
            'partner_id': partner_id,
        }
        return self._create_and_init(vals)

    @api.model
    def create_from_recent(self, phonecall_id):
        recent_phonecall = self.browse(phonecall_id)
        vals = {
            'name': _('Call to %s', recent_phonecall.phone),
            'phone': recent_phonecall.phone,
            'mobile': recent_phonecall.mobile,
            'partner_id': recent_phonecall.partner_id.id,
        }
        return self._create_and_init(vals)

    @api.model
    def create_from_number(self, number):
        vals = {
            'name': _('Call to %s', number),
            'phone': number,
        }
        return self._create_and_init(vals)

    def create_from_missed_call(self, number, partner_id=False):
        self.ensure_one()
        vals = {
            'direction': 'incoming',
            'name': _('Missed Call from %s', number),
            'phone': number,
            'state': 'missed',
            'partner_id': partner_id,
        }
        return self._update_and_init(vals)

    def create_from_rejected_call(self, number, partner_id=False):
        self.ensure_one()
        vals = {
            'direction': 'incoming',
            'name': _('Rejected Incoming Call from %s', number),
            'phone': number,
            'state': 'rejected',
            'partner_id': partner_id,
        }
        return self._update_and_init(vals)

    def create_from_incoming_call_accepted(self, number, partner_id=False):
        self.ensure_one()
        vals = {
            'direction': 'incoming',
            'name': _('Incoming call from %s', number),
            'phone': number,
            'state': 'done',
            'partner_id': partner_id,
        }
        return self._update_and_init(vals)

    @api.model
    def create_from_incoming_call(self, number, partner_id=False):
        if partner_id:
            name = _('Incoming call from %s', self.env['res.partner'].browse([partner_id]).display_name)
        else:
            name = _('Incoming call from %s', number)
        vals = {
            'direction': 'incoming',
            'name': name,
            'phone': number,
            'partner_id': partner_id,
        }
        return self._create_and_init(vals)

    @api.model
    def create_from_phone_widget(self, model, res_id, number):
        partner_id = False
        if model == 'res.partner':
            partner_id = res_id
        else:
            record = self.env[model].browse(res_id)
            fields = self.env[model]._fields.items()
            partner_field_name = [k for k, v in fields if v.type == 'many2one' and v.comodel_name == 'res.partner'][0]
            if len(partner_field_name):
                partner_id = record[partner_field_name].id
        vals = {
            'name': _('Call to %s', number),
            'phone': number,
            'partner_id': partner_id,
        }
        return self._create_and_init(vals)

    @api.model
    def get_from_activity_id(self, activity_id):
        phonecall = self.search([('activity_id', '=', activity_id)])
        phonecall.date_deadline = fields.Date.today()
        phonecall.init_call()
        return phonecall._get_info()[0]
