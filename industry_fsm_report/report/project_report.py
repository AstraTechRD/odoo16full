# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _name = 'report.project.task.user.fsm'
    _inherit = 'report.project.task.user.fsm'

    worksheet_template_id = fields.Many2one('worksheet.template', string="Worksheet Template", readonly=True)

    def _select(self):
        select_to_append = """,
            t.worksheet_template_id as worksheet_template_id
        """
        return super()._select() + select_to_append

    def _group_by(self):
        group_by_append = """,
                t.worksheet_template_id
        """
        return super(ReportProjectTaskUser, self)._group_by() + group_by_append
