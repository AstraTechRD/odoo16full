# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime
import pytz

from odoo import Command, fields, models, api, _
from odoo.osv import expression


class Task(models.Model):
    _inherit = "project.task"

    @api.model
    def default_get(self, fields_list):
        result = super(Task, self).default_get(fields_list)
        is_fsm_mode = self._context.get('fsm_mode')
        if 'project_id' in fields_list and not result.get('project_id') and is_fsm_mode:
            company_id = self.env.context.get('default_company_id') or self.env.company.id
            fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', company_id)], order='sequence', limit=1)
            if fsm_project:
                result['stage_id'] = self.stage_find(fsm_project.id, [('fold', '=', False)])
            result['project_id'] = fsm_project.id

        date_begin = result.get('planned_date_begin')
        date_end = result.get('planned_date_end')
        if is_fsm_mode and (date_begin or date_end):
            if not date_begin:
                date_begin = date_end.replace(hour=0, minute=0, second=1)
            if not date_end:
                date_end = date_begin.replace(hour=23, minute=59, second=59)
            date_diff = date_end - date_begin
            if date_diff.seconds / 3600 > 23.5:
                # if the interval between both dates are more than 23 hours and 30 minutes
                # then we changes those dates to fit with the working schedule of the assigned user or the current company
                # because we assume here, the planned dates are not the ones chosen by the current user.
                user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
                date_begin = pytz.utc.localize(date_begin).astimezone(user_tz)
                date_end = pytz.utc.localize(date_end).astimezone(user_tz)
                user_ids_list = [res[2] for res in result.get('user_ids', []) if len(res) == 3 and res[0] == Command.SET]  # user_ids = [(Command.SET, 0, <user_ids>)]
                user_ids = user_ids_list[-1] if user_ids_list else []
                users = self.env['res.users'].sudo().browse(user_ids)
                user = len(users) == 1 and users
                if user and user.employee_id:  # then the default start/end hours correspond to what is configured on the employee calendar
                    resource_calendar = user.resource_calendar_id
                else:  # Otherwise, the default start/end hours correspond to what is configured on the company calendar
                    company = self.env['res.company'].sudo().browse(result.get('company_id')) if result.get(
                        'company_id') else self.env.user.company_id
                    resource_calendar = company.resource_calendar_id
                if resource_calendar:
                    resources_work_intervals = resource_calendar._work_intervals_batch(date_begin, date_end)
                    work_intervals = [(start, stop) for start, stop, meta in resources_work_intervals[False]]
                    if work_intervals:
                        planned_date_begin = work_intervals[0][0]
                        planned_date_end = work_intervals[0][1]
                        for dummy, stop in work_intervals[1:]:
                            if stop.date() != planned_date_begin.date():  # when it is no longer the case we keep the previous stop date.
                                break
                            planned_date_end = stop
                        result['planned_date_begin'] = planned_date_begin.astimezone(pytz.utc).replace(tzinfo=None)
                        result['planned_date_end'] = planned_date_end.astimezone(pytz.utc).replace(tzinfo=None)
                else:
                    result['planned_date_begin'] = date_begin.replace(hour=9, minute=0, second=1).astimezone(pytz.utc).replace(tzinfo=None)
                    result['planned_date_end'] = date_end.astimezone(pytz.utc).replace(tzinfo=None)
        return result

    allow_worksheets = fields.Boolean(related='project_id.allow_worksheets')
    is_fsm = fields.Boolean(related='project_id.is_fsm', search='_search_is_fsm')
    fsm_done = fields.Boolean("Task Done", compute='_compute_fsm_done', readonly=False, store=True, copy=False)
    partner_id = fields.Many2one(group_expand='_read_group_partner_id')
    project_id = fields.Many2one(group_expand='_read_group_project_id')
    user_ids = fields.Many2many(group_expand='_read_group_user_ids')
    # Use to count conditions between : time, worksheet and materials
    # If 2 over 3 are enabled for the project, the required count = 2
    # If 1 over 3 is met (enabled + encoded), the satisfied count = 2
    display_enabled_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_satisfied_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_mark_as_done_primary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    display_mark_as_done_secondary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    display_sign_report_primary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_sign_report_secondary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_send_report_primary = fields.Boolean(compute='_compute_display_send_report_buttons')
    display_send_report_secondary = fields.Boolean(compute='_compute_display_send_report_buttons')
    worksheet_signature = fields.Binary('Signature', copy=False, attachment=True)
    worksheet_signed_by = fields.Char('Signed By', copy=False)
    fsm_is_sent = fields.Boolean('Is Worksheet sent', readonly=True)
    comment = fields.Html(string='Comments', copy=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'allow_worksheets',
                                              'is_fsm',
                                              'planned_date_begin',
                                              'planned_date_end',
                                              'fsm_done',
                                              'partner_phone',
                                              'partner_city',}

    @api.depends(
        'fsm_done', 'is_fsm', 'timer_start',
        'display_enabled_conditions_count', 'display_satisfied_conditions_count')
    def _compute_mark_as_done_buttons(self):
        for task in self:
            primary, secondary = True, True
            if task.fsm_done or not task.is_fsm or task.timer_start:
                primary, secondary = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    secondary = False
                else:
                    primary = False
            task.update({
                'display_mark_as_done_primary': primary,
                'display_mark_as_done_secondary': secondary,
            })

    @api.depends('allow_worksheets', 'project_id.allow_timesheets', 'total_hours_spent', 'comment')
    def _compute_display_conditions_count(self):
        for task in self:
            enabled = 1 if task.project_id.allow_timesheets else 0
            satisfied = 1 if enabled and task.total_hours_spent else 0
            enabled += 1 if task.allow_worksheets else 0
            satisfied += 1 if task.allow_worksheets and task.comment else 0
            task.update({
                'display_enabled_conditions_count': enabled,
                'display_satisfied_conditions_count': satisfied
            })

    @api.depends('fsm_done', 'display_timesheet_timer', 'timer_start', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        fsm_done_tasks = self.filtered(lambda task: task.fsm_done)
        fsm_done_tasks.update({
            'display_timer_start_primary': False,
            'display_timer_start_secondary': False,
            'display_timer_stop': False,
            'display_timer_pause': False,
            'display_timer_resume': False,
        })
        super(Task, self - fsm_done_tasks)._compute_display_timer_buttons()

    def _hide_sign_button(self):
        self.ensure_one()
        return not self.allow_worksheets or self.timer_start or self.worksheet_signature \
            or not self.display_satisfied_conditions_count

    @api.depends(
        'allow_worksheets', 'timer_start', 'worksheet_signature',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count')
    def _compute_display_sign_report_buttons(self):
        for task in self:
            sign_p, sign_s = True, True
            if task._hide_sign_button():
                sign_p, sign_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    sign_s = False
                else:
                    sign_p = False
            task.update({
                'display_sign_report_primary': sign_p,
                'display_sign_report_secondary': sign_s,
            })

    def _hide_send_report_button(self):
        self.ensure_one()
        return not self.allow_worksheets or self.timer_start or not self.display_satisfied_conditions_count \
            or self.fsm_is_sent

    @api.depends(
        'allow_worksheets', 'timer_start',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count',
        'fsm_is_sent')
    def _compute_display_send_report_buttons(self):
        for task in self:
            send_p, send_s = True, True
            if task._hide_send_report_button():
                send_p, send_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    send_s = False
                else:
                    send_p = False
            task.update({
                'display_send_report_primary': send_p,
                'display_send_report_secondary': send_s,
            })

    @api.model
    def _search_is_fsm(self, operator, value):
        query = """
            SELECT p.id
            FROM project_project P
            WHERE P.active = 't' AND P.is_fsm
        """
        operator_new = operator == "=" and "inselect" or "not inselect"
        return [('project_id', operator_new, (query, ()))]

    @api.model
    def _read_group_partner_id(self, partners, domain, order):
        if self._context.get('fsm_mode'):
            dom_tuples = [dom for dom in domain if isinstance(dom, (list, tuple)) and len(dom) == 3]
            if any(d[0] == 'partner_id' and d[1] in ('=', 'ilike', 'child_of') for d in dom_tuples):
                filter_domain = self._expand_domain_m2o_groupby(dom_tuples, 'partner_id')
                return self.env['res.partner'].search(filter_domain, order=order)
        return partners

    @api.model
    def _read_group_project_id(self, projects, domain, order):
        if self._context.get('fsm_mode'):
            dom_tuples = [dom for dom in domain if isinstance(dom, (list, tuple)) and len(dom) == 3]
            if any(d[0] == 'project_id' and d[1] in ('=', 'ilike') for d in dom_tuples):
                filter_domain = self._expand_domain_m2o_groupby(dom_tuples, 'project_id')
                domain = expression.AND([filter_domain, [('is_fsm', '=', True)]])
                return self.env['project.project'].search(domain, order=order)
        return projects

    @api.model
    def _expand_domain_m2o_groupby(self, domain, filter_field):
        filter_domain = []
        for dom in domain:
            if dom[0] == filter_field:
                field = self._fields[dom[0]]
                if field.type == 'many2one' and len(dom) == 3:
                    if dom[1] == '=':
                        filter_domain = expression.OR([filter_domain, [('id', dom[1], dom[2])]])
                    elif dom[1] == 'ilike':
                        rec_name = self.env[field.comodel_name]._rec_name
                        filter_domain = expression.OR([filter_domain, [(rec_name, dom[1], dom[2])]])
                    elif dom[1] == 'child_of':
                        rec_name = self.env[field.comodel_name]._rec_name
                        filter_domain = expression.OR([filter_domain, [(rec_name, 'ilike', dom[2])]])
        return filter_domain

    @api.model
    def _read_group_user_ids(self, users, domain, order):
        if self.env.context.get('fsm_mode'):
            recently_created_tasks = self.env['project.task'].search([
                ('create_date', '>', datetime.now() - timedelta(days=30)),
                ('is_fsm', '=', True),
                ('user_ids', '!=', False)
            ])
            search_domain = ['&', ('company_id', 'in', self.env.companies.ids), '|', '|', ('id', 'in', users.ids), ('groups_id', 'in', self.env.ref('industry_fsm.group_fsm_user').id), ('id', 'in', recently_created_tasks.mapped('user_ids.id'))]
            return users.search(search_domain, order=order)
        return users

    def _compute_fsm_done(self):
        closed_tasks = self.filtered('is_closed')
        closed_tasks.fsm_done = True

    def action_fsm_worksheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': self.id,
            'view_mode': 'form',
            'context': {'form_view_initial_mode': 'edit', 'task_worksheet_comment': True},
            'views': [[self.env.ref('industry_fsm.fsm_form_view_comment').id, 'form']],
        }

    def action_view_timesheets(self):
        kanban_view = self.env.ref('hr_timesheet.view_kanban_account_analytic_line')
        form_view = self.env.ref('industry_fsm.timesheet_view_form')
        tree_view = self.env.ref('industry_fsm.timesheet_view_tree_user_inherit')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Time'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form,kanban',
            'views': [(tree_view.id, 'list'), (kanban_view.id, 'kanban'), (form_view.id, 'form')],
            'domain': [('task_id', '=', self.id), ('project_id', '!=', False)],
            'context': {
                'fsm_mode': True,
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            }
        }

    def action_fsm_validate(self, stop_running_timers=False):
        """ Moves Task to next stage.
            If allow billable on task, timesheet product set on project and user has privileges :
            Create SO confirmed with time and material.
        """
        Timer = self.env['timer.timer']
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', 'in', self.ids)])
        timesheets = self.env['account.analytic.line'].sudo().search([('task_id', 'in', self.ids)])
        timesheets_running_timer_ids = None
        if timesheets:
            timesheets_running_timer_ids = Timer.search([
                ('res_model', '=', 'account.analytic.line'),
                ('res_id', 'in', timesheets.ids)])
        if tasks_running_timer_ids or timesheets_running_timer_ids:
            if stop_running_timers:
                self._stop_all_timers_and_create_timesheets(tasks_running_timer_ids, timesheets_running_timer_ids, timesheets)
            else:
                wizard = self.env['project.task.stop.timers.wizard'].create({
                    'line_ids': [Command.create({'task_id': task.id}) for task in self],
                })
                return {
                    'name': _('Do you want to stop the running timers?'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_id': self.env.ref('industry_fsm.view_task_stop_timer_wizard_form').id,
                    'target': 'new',
                    'res_model': 'project.task.stop.timers.wizard',
                    'res_id': wizard.id,
                }

        closed_stage_by_project = {
            project.id:
                project.type_ids.filtered(lambda stage: stage.fold)[:1] or project.type_ids[-1:]
            for project in self.project_id
        }
        for task in self:
            # determine closed stage for task
            closed_stage = closed_stage_by_project.get(self.project_id.id)
            values = {'fsm_done': True}
            if closed_stage:
                values['stage_id'] = closed_stage.id

            task.write(values)

        return True

    @api.model
    def _stop_all_timers_and_create_timesheets(self, tasks_running_timer_ids, timesheets_running_timer_ids, timesheets):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        Timesheet = self.env['account.analytic.line']

        if not tasks_running_timer_ids and not timesheets_running_timer_ids:
            return Timesheet

        result = Timesheet
        minimum_duration = int(ConfigParameter.get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(ConfigParameter.get_param('timesheet_grid.timesheet_rounding', 0))
        if tasks_running_timer_ids:
            task_dict = {task.id: task for task in self}
            timesheets_vals = []
            for timer in tasks_running_timer_ids:
                minutes_spent = timer._get_minutes_spent()
                time_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding) / 60
                task = task_dict[timer.res_id]
                timesheets_vals.append({
                    'task_id': task.id,
                    'project_id': task.project_id.id,
                    'user_id': timer.user_id.id,
                    'unit_amount': time_spent,
                })
            tasks_running_timer_ids.sudo().unlink()
            result += Timesheet.sudo().create(timesheets_vals)

        if timesheets_running_timer_ids:
            timesheets_dict = {timesheet.id: timesheet for timesheet in timesheets}
            for timer in timesheets_running_timer_ids:
                timesheet = timesheets_dict[timer.res_id]
                minutes_spent = timer._get_minutes_spent()
                timesheet._add_timesheet_time(minutes_spent)
                result += timesheet
            timesheets_running_timer_ids.sudo().unlink()

        return result

    def action_fsm_navigate(self):
        if not self.partner_id.city or not self.partner_id.country_id:
            return {
                'name': _('Customer'),
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'view_mode': 'form',
                'view_id': self.env.ref('industry_fsm.view_partner_address_form_industry_fsm').id,
                'target': 'new',
            }
        return self.partner_id.action_partner_navigate()

    def action_preview_worksheet(self):
        self.ensure_one()
        source = 'fsm' if self._context.get('fsm_mode', False) else 'project'
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(query_string=f'&source={source}')
        }

    def action_send_report(self):
        tasks_with_report = self.filtered(lambda task: task._is_fsm_report_available())
        if not tasks_with_report:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("There are no reports to send."),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        template_id = self.env.ref('industry_fsm.mail_template_data_task_report').id
        return {
            'name': _("Send report"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass_mail' if len(tasks_with_report.ids) > 1 else 'comment',
                'default_model': 'project.task',
                'default_res_id': tasks_with_report.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'fsm_mark_as_sent': True,
                'active_ids': tasks_with_report.ids,
            },
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Worksheet %s - %s' % (self.name, self.partner_id.name)

    def _is_fsm_report_available(self):
        self.ensure_one()
        return self.comment or self.timesheet_ids

    def has_to_be_signed(self):
        self.ensure_one()
        return self._is_fsm_report_available() and not self.worksheet_signature

    @api.model
    def get_views(self, views, options=None):
        options['toolbar'] = not self._context.get('task_worksheet_comment') and options.get('toolbar')
        res = super().get_views(views, options)
        return res

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _message_post_after_hook(self, message, *args, **kwargs):
        if self.env.context.get('fsm_mark_as_sent') and not self.fsm_is_sent:
            self.fsm_is_sent = True
