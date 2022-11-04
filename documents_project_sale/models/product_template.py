# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    documents_allowed_company_id = fields.Many2one('res.company', compute='_compute_documents_allowed_company_id')
    template_folder_id = fields.Many2one('documents.folder', "Workspace Template", company_dependent=True, copy=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', documents_allowed_company_id)]",
        help="On sales order confirmation, a workspace will be automatically generated for the project based on this template.")

    @api.depends('company_id')
    def _compute_documents_allowed_company_id(self):
        for template in self:
            template.documents_allowed_company_id = template.company_id if template.company_id else self.env.company
