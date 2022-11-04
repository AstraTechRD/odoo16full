# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _start_name = "date_planned_start"
    _stop_name = "date_planned_finished"

    check_ids = fields.One2many('quality.check', 'production_id', string="Checks")

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        productions = super()._split_productions(amounts=amounts, cancel_remaining_qty=cancel_remaining_qty, set_consumed_qty=set_consumed_qty)
        backorders = productions[1:]
        if not backorders:
            return productions
        for wo in backorders.workorder_ids:
            if wo.current_quality_check_id.component_id:
                wo.current_quality_check_id._update_component_quantity()
        return productions
