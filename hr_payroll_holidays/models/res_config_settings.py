# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _domain_company(self):
        company = self.env.company
        return ['|', ('company_id', '=', False), ('company_id', '=', company.id)]

    deferred_time_off_manager = fields.Many2one('res.users', related='company_id.deferred_time_off_manager', domain=_domain_company, readonly=False)
