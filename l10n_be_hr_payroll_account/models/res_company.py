# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    exemption_doctor_master_account_id = fields.Many2one('account.account')
    exemption_bachelor_account_id = fields.Many2one('account.account')
    exemption_bachelor_capping_account_id = fields.Many2one('account.account')
    exemption_journal_id = fields.Many2one('account.journal', 'Salary Journal', domain="[('company_id', '=', company_id)]")
