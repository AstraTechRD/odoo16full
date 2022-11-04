# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PlanningTemplate(models.Model):
    _inherit = 'planning.slot.template'

    project_id = fields.Many2one('project.project', string="Project",
                                 company_dependent=True, domain="[('allow_forecast', '=', True)]", copy=True)

    def name_get(self):
        name_template = super(PlanningTemplate, self).name_get()
        name_dict = dict([(x[0], x[1]) for x in name_template])
        result = []
        for shift_template in self:
            if shift_template.project_id:
                name = '%s [%s]' % (name_dict[shift_template.id], shift_template.project_id.display_name[:30])
            else:
                name = name_dict[shift_template.id]
            result.append([shift_template.id, name])
        return result
