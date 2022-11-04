# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    skill_ids = fields.One2many('hr.appraisal.skill', 'appraisal_id', string="Skills")

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'pending':
            new_appraisals = self.filtered(lambda a: a.state == 'new')
            new_appraisals._copy_skills_when_confirmed()

        if 'state' in vals and vals['state'] == 'done':
            for appraisal in self:
                employee_skills = appraisal.employee_id.employee_skill_ids
                appraisal_skills = appraisal.skill_ids
                updated_skills = []
                deleted_skills = []
                added_skills = []
                for employee_skill in employee_skills.filtered(lambda s: s.skill_id in appraisal_skills.skill_id):
                    appraisal_skill = appraisal_skills.filtered(lambda a: a.skill_id == employee_skill.skill_id)
                    if employee_skill.level_progress != appraisal_skill.level_progress:
                        updated_skills.append({
                            'name': employee_skill.skill_id.name,
                            'old_level': employee_skill.level_progress,
                            'new_level': appraisal_skill.level_progress,
                            'justification': appraisal_skill.justification,
                        })

                deleted_skills = employee_skills.filtered(lambda s: s.skill_id not in appraisal_skills.skill_id).mapped('skill_id.name')
                added_skills = appraisal_skills.filtered(lambda a: a.skill_id not in employee_skills.skill_id).mapped('skill_id.name')

                employee_skills.sudo().unlink()
                self.env['hr.employee.skill'].sudo().create([{
                    'employee_id': appraisal.employee_id.id,
                    'skill_id': skill.skill_id.id,
                    'skill_level_id': skill.skill_level_id.id,
                    'skill_type_id': skill.skill_type_id.id,
                } for skill in appraisal_skills])

                if len(updated_skills + added_skills + deleted_skills) > 0:
                    rendered = self.env['ir.qweb']._render('hr_appraisal_skills.appraisal_skills_update_template', {
                        'updated_skills': updated_skills,
                        'added_skills': added_skills,
                        'deleted_skills': deleted_skills,
                    }, raise_if_not_found=False)
                    appraisal.message_post(body=rendered)
        result = super(HrAppraisal, self).write(vals)
        return result

    def _copy_skills_when_confirmed(self):
        for appraisal in self:
            employee_skills = appraisal.employee_id.employee_skill_ids
            # in case the employee confirms its appraisal
            self.env['hr.appraisal.skill'].sudo().create([{
                'appraisal_id': appraisal.id,
                'skill_id': skill.skill_id.id,
                'previous_skill_level_id': skill.skill_level_id.id,
                'skill_level_id': skill.skill_level_id.id,
                'skill_type_id': skill.skill_type_id.id,
                'employee_skill_id': skill.id,
            } for skill in employee_skills])


class HrAppraisalSkill(models.Model):
    _name = 'hr.appraisal.skill'
    _description = "Employee Skills"
    _order = "skill_type_id, skill_level_id"

    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='appraisal_id.employee_id', store=True)
    manager_ids = fields.Many2many('hr.employee', compute='_compute_manager_ids', store=True)
    skill_id = fields.Many2one('hr.skill', required=True)
    previous_skill_level_id = fields.Many2one('hr.skill.level')
    skill_level_id = fields.Many2one('hr.skill.level', required=True)
    skill_type_id = fields.Many2one(related='skill_id.skill_type_id', store=True)
    level_progress = fields.Integer(related='skill_level_id.level_progress')
    justification = fields.Char()
    employee_skill_id = fields.Many2one('hr.employee.skill')

    _sql_constraints = [
        ('_unique_skill', 'unique (appraisal_id, skill_id)', "Two levels for the same skill is not allowed"),
    ]

    @api.depends('appraisal_id')
    def _compute_manager_ids(self):
        for skill in self:
            skill.manager_ids = skill.appraisal_id.manager_ids
