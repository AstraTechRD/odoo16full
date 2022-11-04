# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    is_appraisal = fields.Boolean(
        string="Appraisal Managers Only",
        help="Check this option to restrict the answers to appraisal managers only.")

    def action_survey_user_input_completed(self):
        action = super().action_survey_user_input_completed()
        if self.is_appraisal:
            action.update({
                'domain': [('survey_id.is_appraisal', '=', True)]
            })
        return action

    def action_survey_user_input(self):
        action = super().action_survey_user_input()
        if self.is_appraisal:
            action.update({
                'domain': [('survey_id.is_appraisal', '=', True)]
            })
        return action


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    appraisal_id = fields.Many2one('hr.appraisal')

    def action_open_survey_inputs(self):
        self.ensure_one()
        return {
            'name': _("Survey Feedback"),
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/appraisal/%s/results/?survey_id=%s' % (self.appraisal_id.id, self.survey_id.id),
        }

class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    survey_id = fields.Many2one('survey.survey', related='question_id.survey_id')
