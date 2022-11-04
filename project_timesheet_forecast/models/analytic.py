# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import fields, models
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    slot_id = fields.Many2one('planning.slot', 'Planning Shift')

    def _apply_grid_grouped_expand(
            self, grid_domain, row_fields, built_grids, section_field=None, group_expand_section_values=None):

        grids = super()._apply_grid_grouped_expand(grid_domain, row_fields, built_grids,
            section_field=section_field, group_expand_section_values=group_expand_section_values)

        employee = self.env.user.employee_id
        valid_row_fields = list(set(['project_id', 'employee_id']) & set(row_fields))
        if not employee or not valid_row_fields:
            return grids
        slots = self.env['planning.slot'].read_group(
            self._get_planning_domain(employee.id),
            valid_row_fields, valid_row_fields, lazy=False
        )
        employee_name_get = employee.name_get()[0]

        rows_dict = defaultdict(dict)

        def add_record(slot, label):
            record = {}
            domain = [('id', '=', -1), ('employee_id', '=', employee.id)]
            for row_field in row_fields:
                if row_field in valid_row_fields:
                    record[row_field] = slot[row_field]
                    if row_field != 'employee_id':
                        domain += [(row_field, '=', slot[row_field][0])]
                else:
                    record[row_field] = False
            key = tuple(record.values())
            rows_dict[label][key] = {
                'values': record,
                'domain': domain,
            }

        def find_record(grid, slot):
            for row in grid['rows']:
                for valid_row_field in valid_row_fields:
                    row_fields_value = row['values'][valid_row_field]
                    if row_fields_value and row_fields_value[0] == slot[valid_row_field][0]:
                        return True
            return False

        for slot in slots:
            if section_field:
                employee_grid = next(filter(lambda g: g['__label'] == employee_name_get, grids), False)
                if not find_record(employee_grid, slot):
                    add_record(slot, employee_name_get)
            else:
                if not find_record(grids, slot):
                    add_record(slot, False)

        if rows_dict:
            if section_field:
                read_grid_grouped_result_dict = {grid['__label']: grid for grid in grids}

            for section_id, rows in rows_dict.items():
                rows = sorted(rows.values(), key=lambda l: [
                    l['values'][field]
                    if field not in valid_row_fields
                    else l['values'][field][1] if l['values'][field] else " "
                    for field in row_fields[0:2]
                ])

                if section_field:
                    # grids is a list of dicts
                    domain_section_id = section_id[0]
                    grid_domain = expression.AND([grid_domain, [(section_field, '=', domain_section_id)]])
                    grid_data = read_grid_grouped_result_dict[section_id]
                else:
                    # grids is only a dict
                    grid_data = grids

                grid = [
                    [{**self._grid_make_empty_cell(r['domain'], c['domain'], grid_domain), 'is_current': c.get('is_current', False),
                      'is_unavailable': c.get('is_unavailable', False)} for c in grid_data['cols']]
                    for r in rows]

                if len(rows) > 0:
                    # update grid and rows in result
                    if len(grid_data['rows']) == 0 and len(grid_data['grid']) == 0:
                        grid_data.update(rows=rows, grid=grid)
                    else:
                        grid_data['rows'].extend(rows)
                        grid_data['grid'].extend(grid)
        return grids

    def _group_expand_employee_ids(self, employees, domain, order):
        res = super()._group_expand_employee_ids(employees, domain, order)
        employee = self.env.user.employee_id
        if not employee:
            return res

        slot_id = self.env['planning.slot']._search(
            self._get_planning_domain(employee.id), limit=1
        )
        if slot_id:
            res |= employee
        return res

    def _get_planning_domain(self, employee_id):
        today = fields.Date.to_string(fields.Date.today())
        grid_anchor = fields.Datetime.from_string(self.env.context.get('grid_anchor', today))
        grid_range = self.env.context.get('grid_range', 'week')

        period_start = grid_anchor if grid_range == 'days'\
            else grid_anchor - relativedelta(days=grid_anchor.weekday() + 1) if grid_range == 'week'\
            else grid_anchor + relativedelta(day=1)
        period_end = period_start + relativedelta(**{grid_range + 's': 1})

        planning_domain = [
            ('employee_id', '=', employee_id),
            ('state', '=', 'published'),
            ('project_id', '!=', False),
            ('start_datetime', '<', period_end),
            ('end_datetime', '>', period_start),
        ]
        return planning_domain
