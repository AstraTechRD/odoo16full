# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class VoipQueueMixin(models.AbstractModel):
    _name = 'voip.queue.mixin'
    _description = 'VOIP Queue support'

    has_call_in_queue = fields.Boolean("Is in the Call Queue", compute='_compute_has_call_in_queue')

    def _compute_has_call_in_queue(self):
        domain = self._linked_phone_call_domain()
        call_per_id = {call.activity_id.res_id: True for call in self.env['voip.phonecall'].search(domain)}
        for rec in self:
            rec.has_call_in_queue = call_per_id.get(rec.id, False)

    def _linked_phone_call_domain(self):
        related_activities = self.env['mail.activity']._search([
            ('res_id', 'in', self.ids),
            ('res_model', '=', self._name)
        ], order='res_id')  # In some cases, avoid PostgreSQL to sort output because of the res_id index.
        return [
            ('activity_id', 'in', related_activities),
            ('date_deadline', '<=', fields.Date.today(self)),  # TODO check if correct
            ('in_queue', '=', True),
            ('state', '!=', 'done'),
            ('user_id', '=', self.env.user.id)
        ]

    def create_call_in_queue(self):
        if not self:
            return self.env['mail.activity']

        phonecall_activity_type_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mail_activity_data_call', raise_if_not_found=False)
        if not phonecall_activity_type_id:
            phonecall_activity_type_id = self.env['mail.activity.type'].search(
                ['|', ('res_model', '=', False), ('res_model', '=', self._name),
                 ('category', '=', 'phonecall')], limit=1
            ).id
        if not phonecall_activity_type_id:
            phonecall_activity_type_id = self.env['mail.activity.type'].sudo().create({
                'name': _('Call'),
                'icon': 'fa-phone',
                'category': 'phonecall',
                'delay_count': 2,
                'sequence': 999,
            }).id

        date_deadline = fields.Date.today(self)
        res_model_id = self.env['ir.model']._get_id(self._name)
        activities = self.env['mail.activity'].create([
            {
                'activity_type_id': phonecall_activity_type_id,
                'date_deadline': date_deadline,
                'res_id': record.id,
                'res_model_id': res_model_id,
                'user_id': self.env.uid,
            } for record in self
        ])

        failed_activities = activities.filtered(lambda act: not act.voip_phonecall_id)
        if failed_activities:
            failed_records = self.browse(failed_activities.mapped('res_id'))
            raise UserError(
                _('Some documents cannot be added to the call queue as they do not have a phone number set: %(record_names)s',
                  record_names=', '.join(failed_records.mapped('display_name')))
            )
        return activities

    def delete_call_in_queue(self):
        domain = self._linked_phone_call_domain()
        phonecalls = self.env['voip.phonecall'].search(domain)
        for phonecall in phonecalls:
            phonecall.remove_from_queue()
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'refresh_voip', {})
