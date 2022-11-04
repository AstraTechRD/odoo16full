# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID, _

from . import models
from . import report
from . import wizard


def _generate_assessment_note_ids(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    default_notes = env['res.company']._get_default_assessment_note_ids()
    default_employee_feedback = env['res.company']._get_default_employee_feedback_template()
    default_manager_feedback = env['res.company']._get_default_manager_feedback_template()
    default_confirmation_mail_template = env['res.company']._get_default_appraisal_confirm_mail_template()

    env['res.company'].search([]).write({
        'assessment_note_ids': default_notes,
        'appraisal_employee_feedback_template': default_employee_feedback,
        'appraisal_manager_feedback_template': default_manager_feedback,
        'appraisal_confirm_mail_template': default_confirmation_mail_template.id,
    })

    env['hr.department'].search([]).write({
        'employee_feedback_template': default_employee_feedback,
        'manager_feedback_template': default_manager_feedback,
    })
