# -*- coding: utf-8 -*-
from odoo import _, Command, models, fields


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    def _close(self):
        res = super()._close()
        for timer in self:
            if timer.workorder_id.production_id.analytic_account_id:
                timer._create_analytic_entry()
        return res

    def _create_analytic_entry(self):
        self.ensure_one()
        employee_aal = self.workorder_id.employee_analytic_account_line_ids.filtered(
            lambda line: line.employee_id and line.employee_id == self.employee_id
        )
        duration = self.duration / 60.0
        amount = - duration * self.employee_cost
        if employee_aal:
            employee_aal.write({
                'unit_amount': employee_aal.unit_amount + duration,
                'amount': employee_aal.amount - amount,
            })
        else:
            account = self.workorder_id.production_id.analytic_account_id
            aa_vals = self.workorder_id._prepare_analytic_line_values(account, duration, amount)
            aa_vals['name']: _("[EMPL] %s", self.employee_id.name)
            aa_vals['employee_id'] = self.employee_id.id
            self.workorder_id.employee_analytic_account_line_ids = [Command.create(aa_vals)]


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    employee_analytic_account_line_ids = fields.Many2many('account.analytic.line', copy=False)
