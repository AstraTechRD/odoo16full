# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class DocumentsFolderDeletionWizard(models.TransientModel):
    _name = "documents.folder.deletion.wizard"
    _description = "Documents Folder Deletion Wizard"

    folder_id = fields.Many2one('documents.folder', string='Folder', required=True)
    parent_folder_id = fields.Many2one(related='folder_id.parent_folder_id', string="Parent Folder")

    def delete(self):
        for wizard in self:
            self.env['documents.document'].search([('folder_id', 'child_of', wizard.folder_id.id)]).unlink()
        self.folder_id.unlink()
        return True

    def delete_and_move(self):
        for wizard in self:
            parent_folder = wizard.folder_id.parent_folder_id.ensure_one()
            self.env['documents.document'].search([('folder_id', '=', wizard.folder_id.id)]).write({'folder_id': parent_folder.id})
            wizard.folder_id.children_folder_ids.parent_folder_id = parent_folder
        self.folder_id.unlink()
        return True
