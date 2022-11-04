# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _close_tax_period(self):
        ret = super()._close_tax_period()

        # add a next activity on the moves, as the attachments should be sent to the administration
        MailActivity = self.env['mail.activity'].with_context(mail_activity_quick_update=True)
        activity_type = self.env.ref('account_reports_tax_reminder.mail_activity_type_tax_report_to_be_sent')
        for move in self:
            MailActivity.create({
                'res_id': move.id,
                'res_model_id': self.env.ref('account.model_account_move').id,
                'activity_type_id': activity_type.id,
                'summary': activity_type.summary,
                'note': activity_type.default_note,
                'date_deadline': fields.Date.context_today(move),
                'automated': True,
                'user_id': self.env.user.id,
                'chaining_type': 'suggest', # the next activity should only be created by closing the next tax entry
            })

        return ret
