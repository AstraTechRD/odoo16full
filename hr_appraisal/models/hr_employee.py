# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    next_appraisal_date = fields.Date(
        string='Next Appraisal Date', compute='_compute_next_appraisal_date', groups="hr.group_hr_user",
        help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    last_appraisal_date = fields.Date(
        string='Last Appraisal Date', groups="hr.group_hr_user",
        help="The date of the last appraisal",
        default=fields.Date.today)
    related_partner_id = fields.Many2one('res.partner', compute='_compute_related_partner', groups="hr.group_hr_user")
    ongoing_appraisal_count = fields.Integer(compute='_compute_ongoing_appraisal_count', store=True, groups="hr.group_hr_user")
    appraisal_count = fields.Integer(compute='_compute_appraisal_count', store=True, groups="hr.group_hr_user")
    uncomplete_goals_count = fields.Integer(compute='_compute_uncomplete_goals_count')
    appraisal_ids = fields.One2many('hr.appraisal', 'employee_id')

    def _compute_related_partner(self):
        for rec in self:
            rec.related_partner_id = rec.user_id.partner_id

    @api.depends('appraisal_ids')
    def _compute_appraisal_count(self):
        read_group_result = self.env['hr.appraisal'].with_context(active_test=False).read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in read_group_result)
        for employee in self:
            employee.appraisal_count = result.get(employee.id, 0)

    @api.depends('appraisal_ids.state')
    def _compute_ongoing_appraisal_count(self):
        read_group_result = self.env['hr.appraisal'].with_context(active_test=False).read_group([('employee_id', 'in', self.ids), ('state', 'in', ['new', 'pending'])], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in read_group_result)
        for employee in self:
            employee.ongoing_appraisal_count = result.get(employee.id, 0)

    def _compute_uncomplete_goals_count(self):
        read_group_result = self.env['hr.appraisal.goal'].read_group([('employee_id', 'in', self.ids), ('progression', '!=', '100')], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in read_group_result)
        for employee in self:
            employee.uncomplete_goals_count = result.get(employee.id, 0)

    @api.depends('ongoing_appraisal_count')
    def _compute_next_appraisal_date(self):
        self.filtered('ongoing_appraisal_count').next_appraisal_date = False
        employees_without_appraisal = self.filtered(lambda e: e.ongoing_appraisal_count == 0)
        dates = employees_without_appraisal._upcoming_appraisal_creation_date()
        for employee in employees_without_appraisal:
            employee.next_appraisal_date = dates[employee.id]

    def _upcoming_appraisal_creation_date(self):
        days = int(self.env['ir.config_parameter'].sudo().get_param('hr_appraisal.appraisal_create_in_advance_days', 8))
        today = datetime.date.today()
        dates = {}
        for employee in self:
            if employee.appraisal_count == 0:
                month = employee.company_id.duration_after_recruitment
                starting_date = employee._get_appraisal_plan_starting_date() or today
            else:
                month = employee.company_id.duration_first_appraisal if employee.appraisal_count == 1 else employee.company_id.duration_next_appraisal
                starting_date = employee.last_appraisal_date
            dates[employee.id] = (starting_date or today) + relativedelta(months=month, days=-days)
        return dates

    def _get_appraisal_plan_starting_date(self):
        self.ensure_one()
        return self.create_date
