from ast import literal_eval

from odoo import models, fields
from odoo.http import request


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    allow_employee = fields.Boolean("Requires Log In")
    employee_ids = fields.Many2many(
        'hr.employee', string="employees with access",
        help='if left empty, all employees can log in to the workcenter')
    currency_id = fields.Many2one(related='company_id.currency_id')
    employee_costs_hour = fields.Monetary(string='Employee Hourly Cost', currency_field='currency_id', default=0.0)

    def action_work_order(self):
        action = super().action_work_order()
        # for the call to literal_eval
        context = action.get('context', '{}')
        context = context.replace('active_id', str(self.id))
        action['context'] = dict(literal_eval(context), employee_id=request.session.get('employee_id'))
        return action


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    employee_id = fields.Many2one(
        'hr.employee', string="Employee",
        help='employee that record this working time')

    def _check_open_time_ids(self):
        self.env['mrp.productivity.time']._read_group([
            ('workorder_id', 'in', self.workorder_id.ids),
            ('date_stop', '=', False),
            ('employee_id', '!=', False),
        ], ['employee_id', 'workorder_id'], ['employee_id', 'workorder_id'], lazy=False)
        # TODO make check on employees
