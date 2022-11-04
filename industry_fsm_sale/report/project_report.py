# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models

from odoo.addons.sale.models.sale_order import INVOICE_STATUS


class ReportProjectTaskUser(models.Model):
    _name = 'report.project.task.user.fsm'
    _inherit = 'report.project.task.user.fsm'

    invoice_status = fields.Selection(INVOICE_STATUS, string='Invoice Status', readonly=True)
    remaining_hours_so = fields.Float('Remaining Hours on SO', readonly=True)

    def _select(self):
        select_to_append = """,
            sol.remaining_hours as remaining_hours_so,
            so.invoice_status as invoice_status
        """
        return super()._select() + select_to_append

    def _group_by(self):
        group_by_to_append = """,
            sol.remaining_hours,
            so.invoice_status
        """
        return super()._group_by() + group_by_to_append

    def _from(self):
        from_to_append = """
            LEFT JOIN sale_order_line sol ON t.id = sol.task_id
            LEFT JOIN sale_order so ON t.sale_order_id = so.id
        """
        return super()._from() + from_to_append
