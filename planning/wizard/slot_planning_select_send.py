# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.osv import expression


class SlotPlanningSelectSend(models.TransientModel):
    _name = 'slot.planning.select.send'
    _description = "Select Employees and Send One Slot"

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        if 'employee_ids' in default_fields and res.get('slot_id') and 'employee_ids' not in res:
            slot = self.env['planning.slot'].browse(res['slot_id'])
            if slot:
                domain = [('company_id', '=', slot.company_id.id), ('work_email', '!=', False)]
                if slot.role_id:
                    domain = expression.AND([domain,
                        ['|', ('planning_role_ids', '=', False), ('planning_role_ids', 'in', slot.role_id.id)]])
                res['employee_ids'] = self.env['hr.employee'].sudo().search(domain).ids
        return res

    slot_id = fields.Many2one('planning.slot', "Shifts", required=True, readonly=True)
    company_id = fields.Many2one('res.company', related='slot_id.company_id')
    employee_ids = fields.Many2many('hr.employee', required=True, check_company=True, domain="[('work_email', '!=', False)]")

    def action_send(self):
        if self.slot_id.is_past and not self.slot_id.employee_id:
            # Non-user Planning view do not display unassigned slots in the past
            raise UserError(_('You cannot send a past unassigned slot'))
        return self.slot_id._send_slot(self.employee_ids, self.slot_id.start_datetime, self.slot_id.end_datetime)
