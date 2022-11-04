
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class QualityCheck(models.Model):
    _inherit = "quality.check"

    def action_worksheet_check(self):
        self.ensure_one()
        self.super().action_worksheet_check()
        return self._next()

    def action_fill_sheet(self):
        self.ensure_one()
        return self.action_quality_worksheet()
