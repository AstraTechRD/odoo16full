# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = ['stock.move']

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        so_line = self.group_id.stock_move_ids.sale_line_id[:1]
        lot_id = so_line.sudo().fsm_lot_id or lot_id
        return super()._update_reserved_quantity(need, available_quantity, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
