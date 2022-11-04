# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class TasksConfirmSchedule(models.TransientModel):
    _name = 'project.task.confirm.schedule.wizard'
    _description = 'Task confirm schedule wizard'

    line_ids = fields.One2many('project.task.confirm.schedule.line.wizard', 'parent_id', string="Lines")
    selected_line_count = fields.Integer(compute='_compute_selected_line_count')
    show_warnings = fields.Boolean(compute='_compute_show_warnings')

    # user_id is the same for all lines, hence it is stored here.
    user_id = fields.Many2one('res.users', 'User')

    @api.depends('line_ids.schedule_task')
    def _compute_selected_line_count(self):
        for wizard in self:
            wizard.selected_line_count = len(wizard.line_ids.filtered('schedule_task'))

    @api.depends('line_ids.warning')
    def _compute_show_warnings(self):
        for wizard in self:
            wizard.show_warnings = any(line.warning for line in wizard.line_ids)

    def action_confirm(self):
        self.ensure_one()
        message = ''
        if self.selected_line_count == 0:
            message = _('No task has been scheduled in the future.')
        else:
            self.line_ids._confirm_update(self.user_id)
            if self.selected_line_count == 1:
                message = _('The task has been successfully scheduled.')
            else:
                message = _('The tasks have been successfully scheduled.')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class TasksConfirmScheduleLine(models.TransientModel):
    _name = 'project.task.confirm.schedule.line.wizard'
    _description = 'Task confirm schedule line wizard'

    parent_id = fields.Many2one('project.task.confirm.schedule.wizard', "Wizard", ondelete='cascade')
    task_id = fields.Many2one('project.task', "Task", readonly=True, required=True)
    date_begin = fields.Datetime("Start Date", readonly=True)
    date_end = fields.Datetime("End Date", readonly=True)
    warning = fields.Char('Warning', readonly=True)
    schedule_task = fields.Boolean("Schedule Task", default=True)

    def _confirm_update(self, user):
        for line in self:
            if line.schedule_task:
                line.task_id.with_context(smart_task_scheduling=True).write({
                    'planned_date_begin': line.date_begin,
                    'planned_date_end': line.date_end,
                    'user_ids': user,
                })
