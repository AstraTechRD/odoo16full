# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Project(models.Model):
    _inherit = "project.project"

    worksheet_template_id = fields.Many2one(
        'worksheet.template', compute="_compute_worksheet_template_id", store=True, readonly=False,
        string="Default Worksheet",
        domain="[('res_model', '=', 'project.task'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")

    @api.depends('allow_worksheets')
    def _compute_worksheet_template_id(self):
        default_worksheet = self.env.ref('industry_fsm_report.fsm_worksheet_template', False)
        for project in self:
            if not project.worksheet_template_id:
                if project.allow_worksheets and default_worksheet:
                    project.worksheet_template_id = default_worksheet.id
                else:
                    project.worksheet_template_id = False


class Task(models.Model):
    _inherit = "project.task"

    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        compute='_compute_worksheet_template_id', store=True, readonly=False, tracking=True,
        domain="[('res_model', '=', 'project.task'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]",
        group_expand='_read_group_worksheet_template_id',
        help="Create templates for each type of intervention you have and customize their content with your own custom fields.")
    worksheet_count = fields.Integer(compute='_compute_worksheet_count')
    worksheet_color = fields.Integer(related='worksheet_template_id.color')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {
            'worksheet_count',
            'worksheet_template_id',
        }

    @api.depends('worksheet_count')
    def _compute_display_conditions_count(self):
        super(Task, self)._compute_display_conditions_count()
        for task in self:
            if task.allow_worksheets and task.worksheet_count:
                task.display_satisfied_conditions_count += 1

    def _hide_sign_button(self):
        self.ensure_one()
        return super()._hide_sign_button() or not self.worksheet_template_id

    @api.depends('worksheet_template_id')
    def _compute_display_sign_report_buttons(self):
        super()._compute_display_sign_report_buttons()

    def _hide_send_report_button(self):
        self.ensure_one()
        return super()._hide_send_report_button() or not self.worksheet_template_id

    @api.depends('worksheet_template_id')
    def _compute_display_send_report_buttons(self):
        super()._compute_display_send_report_buttons()

    @api.depends('project_id')
    def _compute_worksheet_template_id(self):
        # Change worksheet when the project changes, not project.allow_worksheet (YTI To confirm)
        for task in self:
            if task.project_id.allow_worksheets:
                task.worksheet_template_id = task.project_id.worksheet_template_id.id
            else:
                task.worksheet_template_id = False

    @api.depends('worksheet_template_id')
    def _compute_worksheet_count(self):
        is_portal_user = self.env.user.share
        for record in self:
            worksheet_count = 0
            if record.worksheet_template_id:
                Worksheet = self.env[record.worksheet_template_id.sudo().model_id.model]
                if is_portal_user:
                    Worksheet = Worksheet.sudo()
                worksheet_count = Worksheet.search_count([('x_project_task_id', '=', record.id)])
            record.worksheet_count = worksheet_count

    @api.model
    def _read_group_worksheet_template_id(self, worksheets, domain, order):
        if self._context.get('fsm_mode'):
            dom_tuples = [dom for dom in domain if isinstance(dom, (list, tuple)) and len(dom) == 3]
            if any(d[0] == 'worksheet_template_id' and d[1] in ('=', 'ilike') for d in dom_tuples):
                filter_domain = self._expand_domain_m2o_groupby(dom_tuples, 'worksheet_template_id')
                return self.env['worksheet.template'].search(filter_domain, order=order)
        return worksheets

    def action_fsm_worksheet(self):
        # We check that comment is not empty, otherwise it means that a `worksheet` has been generated
        # through the use of the mail template in fsm (obviously prior installing industry_fsm_report)
        if not self.worksheet_template_id or self.comment:
            return super(Task, self).action_fsm_worksheet()
        action = self.worksheet_template_id.action_id.sudo().read()[0]
        worksheet = self.env[self.worksheet_template_id.sudo().model_id.model].search([('x_project_task_id', '=', self.id)])
        context = literal_eval(action.get('context', '{}'))
        action.update({
            'res_id': worksheet.id if worksheet else False,
            'views': [(False, 'form')],
            'context': {
                **context,
                'edit': True,
                'default_x_project_task_id': self.id,
                'form_view_initial_mode': 'edit',
            },
        })
        return action

    def _is_fsm_report_available(self):
        self.ensure_one()
        return self.worksheet_count or self.timesheet_ids

class ProjectTaskRecurrence(models.Model):
    _inherit = 'project.task.recurrence'

    @api.model
    def _get_recurring_fields(self):
        return ['worksheet_template_id'] + super(ProjectTaskRecurrence, self)._get_recurring_fields()
