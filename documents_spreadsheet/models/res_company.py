# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _spreadsheet_folder_domain(self):
        return ['|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)]

    documents_spreadsheet_folder_id = fields.Many2one('documents.folder', domain=_spreadsheet_folder_domain,
        default=lambda self: self.env.ref('documents_spreadsheet.documents_spreadsheet_folder', raise_if_not_found=False))
