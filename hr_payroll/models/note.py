# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

class Note(models.Model):
    _inherit = 'note.note'

    def action_add_follower(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.wizard.invite',
            'view_mode': 'form',
            'name': _('Invite Follower'),
            'target': 'new',
            'context': {
                'default_res_model': 'note.note',
                'default_res_id': self.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        notes = super().create(vals_list)
        dashboard_note_tag = self.env.ref('hr_payroll.payroll_note_tag', raise_if_not_found=False)
        if not dashboard_note_tag:
            return notes
        notes_to_subscribe = notes.filtered(lambda note: dashboard_note_tag in note.tag_ids)
        if notes_to_subscribe:
            notes_to_subscribe.note_subscribe_payroll_users()
        return notes

    def write(self, values):
        dashboard_note_tag = self.env.ref('hr_payroll.payroll_note_tag', raise_if_not_found=False)
        if 'tag_ids' in values and dashboard_note_tag:
            notes_without_tag = self.filtered(lambda n: dashboard_note_tag not in n.tag_ids)
        res = super().write(values)
        # check if dashboard note tag was added to add payroll users as followers.
        if 'tag_ids' in values and dashboard_note_tag:
            notes_with_tag = self.filtered(lambda n: dashboard_note_tag in n.tag_ids)
            notes_to_subscribe = notes_without_tag - notes_with_tag
            # If the dashboard note tag is removed, we don't remove them
            if notes_to_subscribe:
                notes_to_subscribe.note_subscribe_payroll_users()
        return res

    def note_subscribe_payroll_users(self):
        payroll_users = self.env.ref('hr_payroll.group_hr_payroll_user').users
        company_payroll_users = payroll_users.filtered(lambda u: self.env.company in u.company_ids)
        self.message_subscribe(partner_ids=company_payroll_users.partner_id.ids)
