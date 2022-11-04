# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    employee_feedback_ids = fields.Many2many('hr.employee', string="Asked Feedback")
    survey_ids = fields.Many2many('survey.survey', help="Sent out surveys")

    def action_ask_feedback(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'appraisal.ask.feedback',
            'target': 'new',
            'name': 'Ask Feedback',
        }

    def action_open_survey_inputs(self):
        self.ensure_one()
        if (self.user_has_groups('hr_appraisal.group_hr_appraisal_manager') or self.env.user.employee_id in self.manager_ids) and len(self.survey_ids) > 1:
            return {
                'name': _("Survey Feedback"),
                'type': 'ir.actions.act_window',
                "views": [[self.env.ref('hr_appraisal_survey.survey_user_input_view_tree').id, 'tree']],
                'view_mode': 'tree',
                'res_model': 'survey.user_input',
                'domain': [('appraisal_id', 'in', self.ids)],
            }
        return {
            'type': 'ir.actions.act_url',
            'name': _("Survey Feedback"),
            'target': 'self',
            'url': '/appraisal/%s/results/' % (self.id)
        }
