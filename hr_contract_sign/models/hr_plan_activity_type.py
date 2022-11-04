# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPlanActivityType(models.Model):
    _inherit = 'hr.plan.activity.type'

    sign_template_id = fields.Many2one(
        'sign.template',
        string='Document to sign')
    employee_role_id = fields.Many2one(
        "sign.item.role",
        string="Employee Role",
        domain="[('id', 'in', sign_template_responsible_ids)]",
        compute="_compute_employee_role_id",
        store=True,
        readonly=False,
        help="Employee's role on the templates to sign. The same role must be present in all the templates")
    sign_template_responsible_ids = fields.Many2many('sign.item.role', compute='_compute_responsible_ids')
    responsible_count = fields.Integer(compute='_compute_responsible_ids')

    is_signature_request = fields.Boolean(compute='_compute_signature_request')

    @api.depends('activity_type_id')
    def _compute_signature_request(self):
        for plan in self:
            plan.is_signature_request = plan.activity_type_id.category == 'sign_request'

    @api.depends('sign_template_id')
    def _compute_responsible_ids(self):
        for plan in self:
            plan.sign_template_responsible_ids = plan.is_signature_request and plan.sign_template_id.sign_item_ids.responsible_id
            plan.responsible_count = len(plan.sign_template_responsible_ids)

    @api.depends('sign_template_responsible_ids')
    def _compute_employee_role_id(self):
        for plan in self:
            if len(plan.sign_template_responsible_ids.ids) == 1:
                plan.employee_role_id = plan.sign_template_responsible_ids._origin
            else:
                plan.employee_role_id = False
