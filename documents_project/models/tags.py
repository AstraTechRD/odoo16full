# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class TagsCategories(models.Model):
    _inherit = "documents.facet"

    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('documents_project_folder') and not res.get('folder_id'):
            res['folder_id'] = self.env.context.get('documents_project_folder')
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = args
        if 'documents_project_folder' in self.env.context:
            folder_id = self.env.context.get('documents_project_folder')
            domain = expression.AND([
                domain,
                [('folder_id', '=', folder_id)]
            ])
        return super()._name_search(name, domain, operator, limit, name_get_uid)
