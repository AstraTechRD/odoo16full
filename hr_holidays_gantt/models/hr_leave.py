# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

from collections import defaultdict
from datetime import timedelta
from itertools import groupby
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang


def format_time(env, time):
    return time.strftime(get_lang(env).time_format)


def format_date(env, date):
    return date.strftime(get_lang(env).date_format)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.model
    def _get_leave_interval(self, date_from, date_to, employee_ids):
        # Validated hr.leave create a resource.calendar.leaves
        calendar_leaves = self.env['resource.calendar.leaves'].search([
            ('time_type', '=', 'leave'),
            '|', ('company_id', 'in', employee_ids.mapped('company_id').ids),
                 ('company_id', '=', False),
            '|', ('resource_id', 'in', employee_ids.mapped('resource_id').ids),
                 ('resource_id', '=', False),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
        ], order='date_from')

        leaves = defaultdict(list)
        for leave in calendar_leaves:
            for employee in employee_ids:
                if (not leave.company_id or leave.company_id == employee.company_id) and\
                   (not leave.resource_id or leave.resource_id == employee.resource_id) and\
                   (not leave.calendar_id or leave.calendar_id == employee.resource_calendar_id):
                    leaves[employee.id].append(leave)

        # Get non-validated time off
        leaves_query = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids.ids),
            ('state', 'in', ['confirm', 'validate1']),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from)
        ], order='date_from')
        for leave in leaves_query:
            leaves[leave.employee_id.id].append(leave)
        return leaves

    def _get_leave_warning(self, leaves, employee, date_from, date_to):
        loc_cache = {}

        def localize(date):
            if date not in loc_cache:
                loc_cache[date] = utc.localize(date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None)
            return loc_cache.get(date)

        warning = ''
        periods = self._group_leaves(leaves, employee, date_from, date_to)
        periods_by_states = [list(b) for a, b in groupby(periods, key=lambda x: x['is_validated'])]

        for periods in periods_by_states:
            period_leaves = ''
            for period in periods:
                dfrom = period['from']
                dto = period['to']
                prefix = ''
                if period != periods[0]:
                    if period == periods[-1]:
                        prefix = _(' and')
                    else:
                        prefix = ','

                if period.get('show_hours', False):
                    period_leaves += _('%(prefix)s from the %(dfrom_date)s at %(dfrom)s to the %(dto_date)s at %(dto)s',
                                        prefix=prefix,
                                        dfrom_date=format_date(self.env, localize(dfrom)),
                                        dfrom=format_time(self.env, localize(dfrom)),
                                        dto_date=format_date(self.env, localize(dto)),
                                        dto=format_time(self.env, localize(dto)))
                else:
                    period_leaves += _('%(prefix)s from the %(dfrom)s to the %(dto)s',
                                        prefix=prefix,
                                        dfrom=format_date(self.env, localize(dfrom)),
                                        dto=format_date(self.env, localize(dto)))

            time_off_type = _('is on time off') if periods[0].get('is_validated') else _('has requested time off')
            warning += _('%(employee)s %(time_off_type)s%(period_leaves)s. \n',
                         employee=employee.name, period_leaves=period_leaves, time_off_type=time_off_type)
        return warning

    def _group_leaves(self, leaves, employee_id, date_from, date_to):
        """
            Returns all the leaves happening between `planned_date_begin` and `planned_date_end`
        """
        work_times = {wk[0]: wk[1] for wk in employee_id.list_work_time_per_day(date_from, date_to)}

        def has_working_hours(start_dt, end_dt):
            """
                Returns `True` if there are any working days between `start_dt` and `end_dt`.
            """
            diff_days = (end_dt - start_dt).days
            all_dates = [start_dt.date() + timedelta(days=delta) for delta in range(diff_days + 1)]
            return any(d in work_times for d in all_dates)

        periods = []
        for leave in leaves:
            if leave.date_from > date_to or leave.date_to < date_from:
                continue

            # Can handle both hr.leave and resource.calendar.leaves
            number_of_days = 0
            is_validated = True
            if issubclass(type(leave), self.pool['hr.leave']):
                number_of_days = leave.number_of_days
                is_validated = False
            else:
                dt_delta = (leave.date_to - leave.date_from)
                number_of_days = dt_delta.days + ((dt_delta.seconds / 3600) / 24)

            if not periods or has_working_hours(periods[-1]['from'], leave.date_to):
                periods.append({'is_validated': is_validated, 'from': leave.date_from, 'to': leave.date_to, 'show_hours': number_of_days <= 1})
            else:
                periods[-1]['is_validated'] = is_validated
                if periods[-1]['to'] < leave.date_to:
                    periods[-1]['to'] = leave.date_to
                periods[-1]['show_hours'] = periods[-1].get('show_hours') or number_of_days <= 1
        return periods

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        employee_ids = set()

        # function to "mark" top level rows concerning employees
        # the propagation of that item to subrows is taken care of in the traverse function below
        def tag_employee_rows(rows):
            for row in rows:
                group_bys = row.get('groupedBy')
                res_id = row.get('resId')
                if group_bys:
                    # if employee_id is the first grouping attribute, we mark the row
                    if group_bys[0] == 'employee_id' and res_id:
                        employee_id = res_id
                        employee_ids.add(employee_id)
                        row['employee_id'] = employee_id
                    # else we recursively traverse the rows where employee_id appears in the group_by
                    elif 'employee_id' in group_bys:
                        tag_employee_rows(row.get('rows'))

        tag_employee_rows(rows)
        employees = self.env['hr.employee'].browse(employee_ids)
        leaves_mapping = employees.mapped('resource_id')._get_unavailable_intervals(start_datetime, end_datetime)

        # function to recursively replace subrows with the ones returned by func
        def traverse(func, row):
            new_row = dict(row)
            if new_row.get('employee_id'):
                for sub_row in new_row.get('rows'):
                    sub_row['employee_id'] = new_row['employee_id']
            new_row['rows'] = [traverse(func, row) for row in new_row.get('rows')]
            return func(new_row)

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unvailabilty(row):
            new_row = dict(row)

            if row.get('employee_id'):
                employee_id = self.env['hr.employee'].browse(row.get('employee_id'))
                if employee_id:
                    # remove intervals smaller than a cell, as they will cause half a cell to turn grey
                    # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
                    # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
                    notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, leaves_mapping[employee_id.resource_id.id])
                    new_row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return new_row

        return [traverse(inject_unvailabilty, row) for row in rows]
