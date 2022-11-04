# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _name = 'report.project.task.user.fsm'
    _inherit = 'report.project.task.user'
    _description = "FSM Tasks Analysis"
    _auto = False

    fsm_done = fields.Boolean('Task Done', readonly=True)

    def _select(self):
        select_to_append = """,
                t.fsm_done as fsm_done
        """
        return super()._select() + select_to_append

    def _group_by(self):
        group_by_append = """,
                t.fsm_done
        """
        return super(ReportProjectTaskUser, self)._group_by() + group_by_append

    def _from(self):
        from_to_append = """
                INNER JOIN project_project pp
                    ON pp.id = t.project_id
                    AND pp.is_fsm = 'true'
        """
        return super()._from() + from_to_append
