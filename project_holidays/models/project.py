# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Task(models.Model):
    _inherit = 'project.task'

    leave_warning = fields.Char(compute='_compute_leave_warning', compute_sudo=True)
    is_absent = fields.Boolean(
        'Employees on Time Off', compute='_compute_leave_warning', search='_search_is_absent',
        compute_sudo=True, readonly=True)

    @api.depends_context('lang')
    @api.depends('planned_date_begin', 'planned_date_end', 'user_ids')
    def _compute_leave_warning(self):
        assigned_tasks = self.filtered(
            lambda t: t.user_ids.employee_id
            and t.project_id
            and t.planned_date_begin
            and t.planned_date_end
            and not t.is_closed
        )
        (self - assigned_tasks).leave_warning = False
        (self - assigned_tasks).is_absent = False

        if not assigned_tasks:
            return

        min_date = min(assigned_tasks.mapped('planned_date_begin'))
        date_from = min_date if min_date > fields.Datetime.today() else fields.Datetime.today()
        leaves = self.env['hr.leave']._get_leave_interval(
            date_from=date_from,
            date_to=max(assigned_tasks.mapped('planned_date_end')),
            employee_ids=assigned_tasks.mapped('user_ids.employee_id')
        )

        for task in assigned_tasks:
            warning = False
            employees = task.user_ids.mapped('employee_id')
            warning = ''
            for employee in employees:
                task_leaves = leaves.get(employee.id)
                if task_leaves:
                    warning += self.env['hr.leave']._get_leave_warning(
                        leaves=task_leaves,
                        employee=employee,
                        date_from=task.planned_date_begin,
                        date_to=task.planned_date_end
                    )
            task.leave_warning = warning or False
            task.is_absent = bool(warning)

    @api.model
    def _search_is_absent(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        tasks = self.search([
            ('user_ids.employee_id', '!=', False),
            ('project_id', '!=', False),
            ('planned_date_begin', '!=', False),
            ('planned_date_end', '!=', False),
            ('is_closed', '!=', True),
        ])
        if not tasks:
            return []

        min_date = min(tasks.mapped('planned_date_begin'))
        date_from = min_date if min_date > fields.Datetime.today() else fields.Datetime.today()
        mapped_leaves = self.env['hr.leave']._get_leave_interval(
            date_from=date_from,
            date_to=max(tasks.mapped('planned_date_end')),
            employee_ids=tasks.mapped('user_ids.employee_id')
        )
        task_ids = []
        for task in tasks:
            employees = tasks.mapped('user_ids.employee_id')
            for employee in employees:
                if employee.id in mapped_leaves:
                    leaves = mapped_leaves[employee.id]
                    period = self.env['hr.leave']._group_leaves(leaves, employee, task.planned_date_begin, task.planned_date_end)
                    if period:
                        task_ids.append(task.id)
        if operator == '!=':
            value = not value
        return [('id', 'in' if value else 'not in', task_ids)]
