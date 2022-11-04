# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def send_followup_snailmail(self, options):
        """
        Send a follow-up report by post to customers in self
        """
        for record in self:
            options['partner_id'] = record.id
            self.env['account.followup.report']._send_snailmail(options)

    def _send_followup(self, options):
        # OVERRIDE account_followup/models/res_partner.py
        super()._send_followup(options)
        followup_line = options.get('followup_line')
        if options.get('snailmail', followup_line.send_email):
            self.send_followup_snailmail(options)
