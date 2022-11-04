# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10nBeIndividualAccount(models.Model):
    _inherit = 'l10n_be.individual.account'

    documents_enabled = fields.Boolean(compute='_compute_documents_enabled')

    @api.depends('company_id.documents_payroll_folder_id', 'company_id.documents_hr_settings')
    def _compute_documents_enabled(self):
        for wizard in self:
            wizard.documents_enabled = self.env.company._payroll_documents_enabled() and all(not line.pdf_to_generate for line in wizard.line_ids)

    def action_post_in_documents(self):
        self.ensure_one()
        if not self.env.company._payroll_documents_enabled():
            return
        self.line_ids.write({'pdf_to_post': True})
        self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()


class L10nBeIndividualAccountLine(models.Model):
    _inherit = 'l10n_be.individual.account.line'

    pdf_to_post = fields.Boolean()

    def _post_pdf(self):
        self.env['documents.document'].create([{
            'owner_id': line.employee_id.user_id.id,
            'datas': line.pdf_file,
            'name': line.pdf_filename,
            'folder_id': self.env.company.documents_payroll_folder_id.id,
            'res_model': 'hr.payslip',  # Security Restriction to payroll managers
        } for line in self])
        template = self.env.ref('documents_l10n_be_hr_payroll.mail_template_individual_account', raise_if_not_found=False)
        if template:
            for line in self:
                template.send_mail(line.employee_id.id, email_layout_xmlid='mail.mail_notification_light')
