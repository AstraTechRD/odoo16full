# -*- coding: utf-8 -*-
from odoo import models, fields


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    employee_id = fields.Many2one('hr.employee', string="Employee")

    def do_pass(self):
        res = super().do_pass()
        if self.workorder_id and self.workorder_id.employee_id:
            self.employee_id = self.workorder_id.employee_id
        return res
