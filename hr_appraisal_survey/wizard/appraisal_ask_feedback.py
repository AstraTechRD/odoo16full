# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError
from odoo.tools import html_sanitize, is_html_empty

_logger = logging.getLogger(__name__)


class AppraisalAskFeedback(models.TransientModel):
    _name = 'appraisal.ask.feedback'
    _inherit = 'mail.composer.mixin'
    _description = "Ask Feedback for Appraisal"

    @api.model
    def default_get(self, fields):
        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        result = super(AppraisalAskFeedback, self).default_get(fields)
        appraisal = self.env['hr.appraisal'].browse(result.get('appraisal_id'))
        if 'survey_template_id' in fields and appraisal and not result.get('survey_template_id'):
            result['survey_template_id'] = appraisal.department_id.appraisal_survey_template_id.id or appraisal.company_id.appraisal_survey_template_id.id
        return result
    appraisal_id = fields.Many2one('hr.appraisal', default=lambda self: self.env.context.get('active_id', None))
    employee_id = fields.Many2one(related='appraisal_id.employee_id', string='Appraisal Employee')
    template_id = fields.Many2one(default=lambda self: self.env.ref('hr_appraisal_survey.mail_template_appraisal_ask_feedback', raise_if_not_found=False))
    user_body = fields.Html('User Contents')

    attachment_ids = fields.Many2many(
        'ir.attachment', 'hr_appraisal_survey_mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', string='Attachments')
    email_from = fields.Char(
        'From', required=True,
        default=lambda self: self.env.user.email_formatted,
    )
    author_id = fields.Many2one(
        'res.partner', string='Author', required=True,
        default=lambda self: self.env.user.partner_id.id,
    )
    survey_template_id = fields.Many2one('survey.survey', required=True, domain=[('is_appraisal', '=', True)])
    employee_ids = fields.Many2many(
        'hr.employee', string="Recipients", required=True)
    deadline = fields.Date(string="Answer Deadline", required=True, compute='_compute_deadline', store=True, readonly=False)

    # Overrides of mail.composer.mixin
    @api.depends('survey_template_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'survey.user_input'

    @api.depends('employee_id')
    def _compute_subject(self):
        for wizard in self.filtered('employee_id'):
            if wizard.template_id:
                wizard.subject = self.sudo()._render_template(wizard.template_id.subject, 'hr.appraisal', wizard.appraisal_id.ids, post_process=True)[wizard.appraisal_id.id]

    @api.depends('appraisal_id.date_close')
    def _compute_deadline(self):
        date_in_month = fields.Date.today() + relativedelta(months=1)
        for wizard in self:
            wizard.deadline = min(date_in_month, wizard.appraisal_id.date_close + relativedelta(days=-1))

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        emailless_employees = self.employee_ids.filtered(lambda e: not (e.work_email or e.user_id.partner_id))
        if emailless_employees:
            emailless_employees_all = self.env['hr.employee'].search(['|', ('work_email', '=', False), ('user_id.partner_id', '=', False)])
            warning = {
                'title': _('Missing email'),
                'message': _('This employee doesn\'t have any mail address registered and will not receive any email. \nThe following employees do not have any email : \n%s',
                        ', '.join(emailless_employees_all.mapped('name'))),
                'type': 'notification',
            }
            self.employee_ids = self.employee_ids - emailless_employees
            return {'warning': warning}

    def _prepare_survey_anwers(self, employees):
        answers = self.env['survey.user_input']
        employees_info = employees.mapped(lambda employee: {
            'id': employee.id,
            'email': employee.work_email or employee.user_id.partner_id.email,
            'partner_id': employee.user_id.partner_id or employee.address_home_id
        })
        emails = [e['email'] for e in employees_info]
        partner_ids = [e['partner_id']['id'] for e in employees_info]

        existing_answers = self.env['survey.user_input'].search([
            '&', '&',
            ('survey_id', '=', self.survey_template_id.id),
            ('appraisal_id', '=', self.appraisal_id.id),
            '|',
            '&', ('partner_id', 'in', partner_ids), ('partner_id', '!=', False),
            '&', ('email', 'in', emails), ('email', '!=', False),
        ])
        employees_done = []
        if existing_answers:
            existing_answer_emails = existing_answers.filtered('email').mapped('email')
            existing_answer_partners_id = existing_answers.filtered('partner_id').mapped('partner_id')
            employees_done = employees_info.filtered(lambda employee:
                employee.email in existing_answer_emails
                or employee.partner_id in existing_answer_partners_id
            )
            existing_answers = existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
            for employee_done in employees_done:
                answer |= existing_answers\
                    .filtered(lambda a:
                        (a.partner_id and a.partner_id == employee_done.partner_id)
                        or (a.email and a.email == employee_done.email)
                    )[:1]

        for new_employee in filter(lambda e: e['id'] not in [e['id'] for e in employees_done], employees_info):
            answers |= self.survey_template_id.sudo()._create_answer(
                partner=new_employee['partner_id'], email=new_employee['email'], check_attempts=False, deadline=self.deadline)
        return answers

    def _send_mail(self, answer):
        """ Create mail specific for recipient containing notably its access token """
        user_body = self.user_body
        user_body = user_body if not is_html_empty(html_sanitize(user_body, strip_style=True, strip_classes=True)) else False
        ctx = {
            'user_body': user_body
        }
        body = self.with_context(**ctx)._render_field('body', answer.ids, post_process=True)[answer.id]
        mail_values = {
            'email_from': self.email_from,
            'author_id': self.author_id.id,
            'model': None,
            'res_id': None,
            'subject': self.subject,
            'body_html': body,
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'auto_delete': True,
        }
        if answer.partner_id:
            mail_values['recipient_ids'] = [Command.link(answer.partner_id.id)]
        else:
            mail_values['email_to'] = answer.email

        template_ctx = {
            'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=self.survey_template_id.title)),
            'model_description': self.env['ir.model']._get('appraisal.ask.feedback').display_name,
            'company': self.env.company,
        }
        body = self.env['ir.qweb']._render('mail.mail_notification_light', template_ctx, minimal_qcontext=True, raise_if_not_found=False)
        if body:
            mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
        else:
            _logger.warning('QWeb template mail.mail_notification_light not found when sending appraisal feedback mails. Sending without layouting.')

        return self.env['mail.mail'].sudo().create(mail_values)

    def action_send(self):
        self.ensure_one()

        answers = self._prepare_survey_anwers(self.employee_ids)
        answers.sudo().write({'appraisal_id': self.appraisal_id.id})
        for answer in answers:
            self._send_mail(answer)

        for employee in self.employee_ids.filtered(lambda e: e.user_id.has_group('hr_appraisal.group_hr_appraisal_user')):
            answer = answers.filtered(lambda l: l.partner_id and l.partner_id == employee.user_id.partner_id)
            if answer:
                self.appraisal_id.with_context(mail_activity_quick_update=True).activity_schedule(
                    'mail.mail_activity_data_todo', self.deadline,
                    summary=_('Fill the feedback form on survey'),
                    note=_('An appraisal feedback was requested. Please take time to fill the <a href="%s" target="_blank">survey</a>') %
                        answer.get_start_url(),
                    user_id=employee.user_id.id)

        self.appraisal_id.employee_feedback_ids |= self.employee_ids
        self.appraisal_id.survey_ids |= self.survey_template_id
        return {'type': 'ir.actions.act_window_close'}
