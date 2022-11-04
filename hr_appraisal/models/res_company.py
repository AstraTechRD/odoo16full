# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools.misc import format_date


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_default_employee_feedback_template(self):
        return """
    <p><b>Does my company recognize my value ?</b></p><p><br><br></p>
    <p><b>What are the elements that would have the best impact on my work performance?</b></p><p><br><br></p>
    <p><b>What are my best achievement(s) since my last appraisal?</b></p><p><br><br></p>
    <p><b>What do I like / dislike about my job, the company or the management?</b></p><p><br><br></p>
    <p><b>How can I improve (skills, attitude, etc)?</b></p><p><br><br></p>"""

    def _get_default_manager_feedback_template(self):
        return """
    <p><b>What are the responsibilities that the employee performs effectively?</b></p><p><br><br></p>
    <p><b>How could the employee improve?</b></p><p><br><br></p>
    <p><b>Short term (6-months) actions / decisions / objectives</b></p><p><br><br></p>
    <p><b>Long term (>6months) career discussion, where does the employee want to go, how to help him reach this path?</b></p><p><br><br></p>"""

    def _get_default_appraisal_confirm_mail_template(self):
        return self.env.ref('hr_appraisal.mail_template_appraisal_confirm', raise_if_not_found=False)

    appraisal_plan = fields.Boolean(string='Automatically Generate Appraisals', default=True)
    assessment_note_ids = fields.One2many('hr.appraisal.note', 'company_id')
    appraisal_employee_feedback_template = fields.Html(default=_get_default_employee_feedback_template)
    appraisal_manager_feedback_template = fields.Html(default=_get_default_manager_feedback_template)
    appraisal_confirm_mail_template = fields.Many2one(
        'mail.template', domain="[('model', '=', 'hr.appraisal')]",
        default=_get_default_appraisal_confirm_mail_template)
    duration_after_recruitment = fields.Integer(string="Create an Appraisal after recruitment", default=6)
    duration_first_appraisal = fields.Integer(string="Create a first Appraisal after", default=6)
    duration_next_appraisal = fields.Integer(string="Create a second Appraisal after", default=12)

    _sql_constraints = [(
        'positif_number_months',
        'CHECK(duration_after_recruitment > 0 AND duration_first_appraisal > 0 AND duration_next_appraisal > 0)',
        "The duration time must be bigger or equal to 1 month."),
    ]

    @api.model
    def _get_default_assessment_note_ids(self):
        return [
            (0, 0, {'name': _('Needs improvement'), 'sequence': '1'}),
            (0, 0, {'name': _('Meets expectations'), 'sequence': '2'}),
            (0, 0, {'name': _('Exceeds expectations'), 'sequence': '3'}),
            (0, 0, {'name': _('Strongly Exceed Expectations'), 'sequence': '4'}),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        default_notes = self._get_default_assessment_note_ids()
        res.sudo().write({'assessment_note_ids': default_notes})
        return res

    def _create_new_appraisal(self, employees):
        days = int(self.env['ir.config_parameter'].sudo().get_param('hr_appraisal.appraisal_create_in_advance_days', 8))
        close_date = datetime.date.today() + relativedelta(days=days)
        appraisal_values = [{
            'company_id': employee.company_id.id,
            'employee_id': employee.id,
            'date_close': close_date,
            'manager_ids': employee.parent_id,
        } for employee in employees]
        return self.env['hr.appraisal'].create(appraisal_values)

    def _get_appraisal_plan_domain(self, current_date):
        self.ensure_one()
        start_date_field = self._get_employee_start_date_field()
        domain = [
                ('company_id', '=', self.id),
                ('ongoing_appraisal_count', '=', 0),
                '|', # After Recruitment
                    '&',
                    '&',
                    ('appraisal_count', '=', 0),
                    (start_date_field, '>', current_date - relativedelta(months=self.duration_after_recruitment + 1, day=1)),
                    (start_date_field, '<=', current_date - relativedelta(months=self.duration_after_recruitment, day=31)),
                '|', # First Appraisal
                    '&',
                    ('appraisal_count', '=', 1),
                    ('last_appraisal_date', '<=', current_date - relativedelta(months=self.duration_first_appraisal)),
                # Next Appraisal
                    '&',
                    ('appraisal_count', '>', 1),
                    ('last_appraisal_date', '<=', current_date - relativedelta(months=self.duration_next_appraisal))
        ]
        return domain

    @api.model
    def _get_employee_start_date_field(self):
        self.ensure_one()
        return 'create_date'

    # CRON job
    def _run_employee_appraisal_plans(self):
        companies = self.env['res.company'].search([('appraisal_plan', '=', True)])
        days = int(self.env['ir.config_parameter'].sudo().get_param('hr_appraisal.appraisal_create_in_advance_days', 8))
        current_date = datetime.date.today() + relativedelta(days=days)

        for company in companies:
            domain = company._get_appraisal_plan_domain(current_date)
            all_employees = self.env['hr.employee'].search(domain)
            if all_employees:
                appraisals = self._create_new_appraisal(all_employees)
                company._generate_activities(appraisals)

    def _generate_activities(self, appraisals):
        self.ensure_one()
        today = fields.Date.today()
        for appraisal in appraisals:
            employee = appraisal.employee_id
            managers = appraisal.manager_ids
            last_appraisal_months = employee.last_appraisal_date and (
                today.year - employee.last_appraisal_date.year)*12 + (today.month - employee.last_appraisal_date.month)
            if employee.user_id:
                # an appraisal has been just created
                if employee.appraisal_count == 1:
                    months = (appraisal.date_close.year - employee.create_date.year) * \
                        12 + (appraisal.date_close.month - employee.create_date.month)
                    note = _("You arrived %s months ago. Your appraisal is created you can assess yourself here. Your manager will determinate the date for your '1to1' meeting.") % (months)
                else:
                    note = _("Your last appraisal was %s months ago. Your appraisal is created you can assess yourself here. Your manager will determinate the date for your '1to1' meeting.") % (
                        last_appraisal_months)
                appraisal.with_context(mail_activity_quick_update=True).activity_schedule(
                    'mail.mail_activity_data_todo', today,
                    summary=_('Appraisal to Confirm and Send'),
                    note=note, user_id=employee.user_id.id)
                for manager in managers.filtered('user_id'):
                    formated_date = format_date(self.env, appraisal.date_close, date_format="MMM d y")
                    if employee.appraisal_count == 1:
                        note = _("The employee %s arrived %s months ago. An appraisal for %s is created. You can assess %s & determinate the date for '1to1' meeting before %s.") % (
                            employee.name, months, employee.name, employee.name, formated_date)
                    else:
                        note = _("Your employee's last appraisal was %s months ago. An appraisal for %s is created. You can assess %s & determinate the date for '1to1' meeting before %s.") % (
                            last_appraisal_months, employee.name, employee.name, formated_date)
                    appraisal.with_context(mail_activity_quick_update=True).activity_schedule(
                        'mail.mail_activity_data_todo', today,
                        summary=_('Appraisal to Confirm and Send'),
                        note=note, user_id=manager.user_id.id)
