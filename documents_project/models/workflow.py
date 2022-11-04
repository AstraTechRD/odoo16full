# -*- coding: utf-8 -*-
from odoo import Command, fields, models, _


class WorkflowActionRuleTask(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('project.task', "Task")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleTask, self).create_record(documents=documents)
        if self.create_model == 'project.task':
            document_msg = _('Task created from document')
            new_obj = self.env[self.create_model].create({
                'name': " / ".join(documents.mapped('name')) or _("New task from Documents"),
                'user_ids': [Command.set(self.env.user.ids)],
                'partner_id': documents.partner_id.id if len(documents.partner_id) == 1 else False,
            })
            task_action = {
                'type': 'ir.actions.act_window',
                'res_model': self.create_model,
                'res_id': new_obj.id,
                'name': "new %s from %s" % (self.create_model, new_obj.name),
                'view_mode': 'form',
                'views': [(False, "form")],
                'context': self._context,
            }
            if len(documents) == 1:
                document_msg += f' {documents._get_html_link()}'
            else:
                document_msg += f's <ul>{"".join(f"<li>{document._get_html_link()}</li>" for document in documents)}</ul>'

            for document in documents:
                this_document = document
                if (document.res_model or document.res_id) and document.res_model != 'documents.document':
                    this_document = document.copy()
                    attachment_id_copy = document.attachment_id.with_context(no_document=True).copy()
                    this_document.write({'attachment_id': attachment_id_copy.id})

                # the 'no_document' key in the context indicates that this ir_attachment has already a
                # documents.document and a new document shouldn't be automatically generated.
                this_document.attachment_id.with_context(no_document=True).write({
                    'res_model': self.create_model,
                    'res_id': new_obj.id
                })
            new_obj.message_post(body=document_msg)
            return task_action
        return rv
