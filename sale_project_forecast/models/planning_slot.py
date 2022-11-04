# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    sale_line_id = fields.Many2one(compute='_compute_sale_line_id', store=True, readonly=False)

    @api.depends('sale_line_id.project_id', 'sale_line_id.task_id.project_id')
    def _compute_project_id(self):
        slot_without_sol_project = self.env['planning.slot']
        for slot in self:
            if not slot.project_id and slot.sale_line_id and (slot.sale_line_id.project_id or slot.sale_line_id.task_id.project_id):
                slot.project_id = slot.sale_line_id.task_id.project_id or slot.sale_line_id.project_id
            else:
                slot_without_sol_project |= slot
        super(PlanningSlot, slot_without_sol_project)._compute_project_id()

    @api.depends('project_id')
    def _compute_sale_line_id(self):
        for slot in self:
            if not slot.sale_line_id and slot.project_id:
                slot.sale_line_id = slot.project_id.sale_line_id

    # -----------------------------------------------------------------
    # ORM Override
    # -----------------------------------------------------------------

    def _name_get_fields(self):
        """ List of fields that can be displayed in the name_get """
        # Ensure this will be displayed in the right order
        name_get_fields = [item for item in super()._name_get_fields() if item not in ['sale_line_id', 'project_id']]
        return name_get_fields + ['sale_line_id', 'project_id']

    # -----------------------------------------------------------------
    # Business methods
    # -----------------------------------------------------------------
