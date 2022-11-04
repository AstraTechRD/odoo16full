# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    planned_date_begin = fields.Datetime("Start date", readonly=True)
    planned_date_end = fields.Datetime("End date", readonly=True)
    planning_overlap = fields.Integer('Planning Overlap', readonly=True, compute='_compute_planning_overlap', search='_search_planning_overlap')

    def _select(self):
        return super(ReportProjectTaskUser, self)._select() + """,
            t.planned_date_begin as planned_date_begin,
            t.planned_date_end as planned_date_end
        """

    def _group_by(self):
        return super(ReportProjectTaskUser, self)._group_by() + """,
            t.planned_date_begin,
            t.planned_date_end
        """

    def _compute_planning_overlap(self):
        overlap_mapping = self.task_id._get_planning_overlap_per_task()
        if not overlap_mapping:
            self.planning_overlap = False
            return
        for task_analysis in self:
            task_analysis.planning_overlap = overlap_mapping.get(task_analysis.id, 0)

    @api.model
    def _search_planning_overlap(self, operator, value):
        return self.env['project.task']._search_planning_overlap(operator, value)
