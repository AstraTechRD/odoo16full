# -*- coding: utf-8 -*-
from odoo import models, fields


class MrpRouting(models.Model):
    _inherit = 'mrp.routing.workcenter'

    employee_ratio = fields.Float("Employee Capacity", default=1, help="Number of employees needed to complete operation.")
