# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid

from datetime import datetime, time
from odoo import fields, models, _, api, Command

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = "hr.employee"

    def _default_employee_token(self):
        return str(uuid.uuid4())

    default_planning_role_id = fields.Many2one('planning.role', string="Default Planning Role",
        compute='_compute_default_planning_role_id', groups='hr.group_hr_user', store=True, readonly=False,
        help="Role that will be selected by default when creating a shift for this employee.\n"
             "This role will also have precedence over the other roles of the employee when planning orders.")
    planning_role_ids = fields.Many2many(related='resource_id.role_ids', readonly=False, groups='hr.group_hr_user',
         help="Roles that the employee can fill in. When creating a shift for this employee, only the shift templates for these roles will be displayed.\n"
             "Similarly, only the open shifts available for these roles will be sent to the employee when the schedule is published.\n"
             "Additionally, the employee will only be assigned orders for these roles (with the default planning role having precedence over the other ones).\n"
             "Leave empty for the employee to be assigned shifts regardless of the role.")
    employee_token = fields.Char('Security Token', default=_default_employee_token, groups='hr.group_hr_user',
                                 copy=False, readonly=True)
    flexible_hours = fields.Boolean(related='resource_id.flexible_hours', readonly=False)

    _sql_constraints = [
        ('employee_token_unique', 'unique(employee_token)', 'Error: each employee token must be unique')
    ]

    def name_get(self):
        if not self.env.context.get('show_job_title'):
            return super().name_get()
        return [(employee.id, employee._get_employee_name_with_job_title()) for employee in self]

    def _get_employee_name_with_job_title(self):
        if self.job_title:
            return "%s (%s)" % (self.name, self.job_title)
        return self.name

    def _init_column(self, column_name):
        # to avoid generating a single default employee_token when installing the module,
        # we need to set the default row by row for this column
        if column_name == "employee_token":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row", self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE employee_token IS NULL" % self._table)
            acc_ids = self.env.cr.dictfetchall()
            query_list = [{'id': acc_id['id'], 'employee_token': self._default_employee_token()} for acc_id in acc_ids]
            query = 'UPDATE ' + self._table + ' SET employee_token = %(employee_token)s WHERE id = %(id)s;'
            self.env.cr._obj.executemany(query, query_list)
        else:
            super(Employee, self)._init_column(column_name)

    def _planning_get_url(self, planning):
        result = {}
        for employee in self:
            if employee.user_id and employee.user_id.has_group('planning.group_planning_user'):
                result[employee.id] = '/web?date_start=%s&date_end=%s#action=planning.planning_action_open_shift&menu_id=' % (planning.date_start, planning.date_end)
            else:
                result[employee.id] = '/planning/%s/%s' % (planning.access_token, employee.employee_token)
        return result

    def _slot_get_url(self, slot):
        action_id = self.env.ref('planning.planning_action_open_shift').id
        menu_id = self.env.ref('planning.planning_menu_root').id
        dbname = self.env.cr.dbname or [''],
        start_date = slot.start_datetime.date() if slot else ''
        end_date = slot.end_datetime.date() if slot else ''
        link = "/web?date_start=%s&date_end=%s#action=%s&model=planning.slot&menu_id=%s&db=%s" % (start_date, end_date, action_id, menu_id, dbname[0])
        return {employee.id: link for employee in self}

    @api.onchange('default_planning_role_id')
    def _onchange_default_planning_role_id(self):
        # Although not recommended the onchange is necessary here as the field is a related and the bellow logic
        # is only needed when editing in order to improve UX.
        for employee in self:
            employee.planning_role_ids |= employee.default_planning_role_id

    @api.depends('planning_role_ids')
    def _compute_default_planning_role_id(self):
        for employee in self:
            if employee.planning_role_ids and employee.default_planning_role_id.id not in employee.planning_role_ids.ids:
                # _origin is required to have it work during onchange calls.
                employee.default_planning_role_id = employee.planning_role_ids._origin[0]
            elif not employee.planning_role_ids:
                employee.default_planning_role_id = False

    def write(self, vals):
        # The following lines had to be written as `planning_role_ids` is a related field that has to depend on
        # `default_planning_role_id`. In order to do so an onchange has been added in order to improve the user
        # experience, but unfortunately does not trigger computation on write. That's why we need to handle it
        # here too.
        default_planning_role_id = vals.get('default_planning_role_id', False)
        default_planning_role = self.env['planning.role'].browse(default_planning_role_id)\
            if isinstance(default_planning_role_id, int) else default_planning_role_id
        if default_planning_role:
            if 'planning_role_ids' in vals and vals['planning_role_ids']:
                # `planning_role_ids` is either a list of commands, a list of ids, or a recordset
                if isinstance(vals['planning_role_ids'], list):
                    if len(vals['planning_role_ids'][0]) == 3:
                        vals['planning_role_ids'].append(Command.link(default_planning_role.id))
                    else:
                        vals['planning_role_ids'].append(default_planning_role.id)
                else:
                    vals['planning_role_ids'] |= default_planning_role
            else:
                vals['planning_role_ids'] = [Command.link(default_planning_role.id)]
        return super().write(vals)

    def action_archive(self):
        res = super().action_archive()
        departure_date = datetime.combine(fields.Date.today(), time.max)
        planning_slots = self.env['planning.slot'].sudo().search([
            ('resource_id', 'in', self.resource_id.ids),
            ('end_datetime', '>=', departure_date),
        ])
        self._manage_archived_employee_shifts(planning_slots, departure_date)
        return res

    def _manage_archived_employee_shifts(self, planning_slots, departure_date):
        shift_vals_list = []
        shift_ids_to_remove_resource = []
        for slot in planning_slots:
            if (slot.start_datetime < departure_date) and (slot.end_datetime > departure_date):
                shift_vals_list.append({
                    'start_datetime': departure_date,
                    'end_datetime': slot.end_datetime,
                    'role_id': slot.role_id.id,
                    'company_id': slot.company_id.id,
                })
                slot.write({'end_datetime': departure_date})
            elif slot.start_datetime >= departure_date:
                shift_ids_to_remove_resource.append(slot.id)
        if shift_vals_list:
            self.env['planning.slot'].sudo().create(shift_vals_list)
        if shift_ids_to_remove_resource:
            self.env['planning.slot'].sudo().browse(shift_ids_to_remove_resource).write({'resource_id': False})

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def action_view_planning(self):
        action = self.env["ir.actions.actions"]._for_xml_id("planning.planning_action_schedule_by_resource")
        action.update({
            'name': _('View Planning'),
            'domain': [('resource_id', 'in', self.resource_id.ids)],
            'context': {
                'search_default_group_by_resource': True,
                'filter_resource_ids': self.resource_id.ids,
                'hide_open_shift': True,
                'default_resource_id': self.resource_id.id if len(self) == 1 else False,
            }
        })
        return action
