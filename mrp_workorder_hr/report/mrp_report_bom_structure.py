# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools import float_round

class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_operation_line(self, product, bom, qty, level, index):
        operation_lines = super()._get_operation_line(product=product, bom=bom, qty=qty, level=level, index=index)
        for operation, line in zip(bom.operation_ids, operation_lines):
            if operation._skip_operation_line(product):
                continue
            capacity = operation.workcenter_id._get_capacity(product)
            operation_cycle = float_round(qty / capacity, precision_rounding=1, rounding_method='UP')
            duration_expected = (operation_cycle * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency) + (operation.workcenter_id.time_stop + operation.workcenter_id.time_start)
            total = ((duration_expected / 60.0) * operation.workcenter_id.employee_costs_hour * operation.employee_ratio)
            line['bom_cost'] += total
        return operation_lines
