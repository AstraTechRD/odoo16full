# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    latest_bom_id = fields.Many2one('mrp.bom', compute="_compute_latest_bom_id")

    @api.depends('bom_id', 'bom_id.active')
    def _compute_latest_bom_id(self):
        self.latest_bom_id = False
        # check if the bom has a new version
        for mo in self:
            if mo.bom_id and not mo.bom_id.active:
                mo.latest_bom_id = mo.bom_id._get_active_version()
        # check if the components have a new version
        mo_to_update = self.search([
            ('id', 'in', self.filtered(lambda p: not p.latest_bom_id).ids),
            ('move_raw_ids.bom_line_id.bom_id.active', '=', False)
        ])
        for mo in mo_to_update:
            mo.latest_bom_id = mo.bom_id

    def action_update_bom(self):
        for production in self:
            if production.state != 'draft' or not production.latest_bom_id:
                continue
            latest_bom = production.latest_bom_id
            (production.move_finished_ids | production.move_raw_ids).unlink()
            production.workorder_ids.unlink()
            production.write({'bom_id': latest_bom.id})
