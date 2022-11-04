# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class HrPlanWizard(models.TransientModel):
    _inherit = 'hr.plan.wizard'

    def _get_activities_to_schedule(self):
        return self.plan_id.plan_activity_type_ids.filtered(lambda a: not a.is_signature_request or a.responsible_count > 2)

    def action_launch(self):
        res = super().action_launch()

        for employee in self.employee_ids:
            for signature_request in self.plan_id.plan_activity_type_ids - self._get_activities_to_schedule():
                employee_role = signature_request.employee_role_id
                responsible = signature_request.get_responsible_id(employee)['responsible']

                self.env['hr.contract.sign.document.wizard'].create({
                    'contract_id': employee.contract_id.id,
                    'employee_ids': [(4, employee.id)],
                    'responsible_id': responsible.id,
                    'employee_role_id': employee_role and employee_role.id,
                    'sign_template_ids': [(4, signature_request.sign_template_id.id)],
                    'subject': _('Signature Request'),
                }).validate_signature()

        return res
