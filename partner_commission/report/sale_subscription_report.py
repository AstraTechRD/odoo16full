# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class SaleSubscriptionReport(models.Model):
    _inherit = 'sale.subscription.report'

    referrer_id = fields.Many2one('res.partner', 'Referrer', readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += ", sub.referrer_id as referrer_id"
        return select_str

    def _group_by(self):
        group_by_str = super()._group_by()
        group_by_str += ", sub.referrer_id"
        return group_by_str
