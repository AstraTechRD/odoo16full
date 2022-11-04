# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.osv import expression


class QualityPoint(models.Model):
    _inherit = "quality.point"

    worksheet_template_id = fields.Many2one(
        'worksheet.template', 'Template',
        domain="[('res_model', '=', 'quality.check'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")
    # tech field used by quality_field_domain widget
    worksheet_model_name = fields.Char(
        'Model Name', related='worksheet_template_id.model_id.model', readonly=True, store=True)
    worksheet_success_conditions = fields.Char('Success Conditions')


class QualityCheck(models.Model):
    _inherit = "quality.check"

    worksheet_template_id = fields.Many2one(
        'worksheet.template', 'Quality Template',
        domain="[('res_model', '=', 'quality.check'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")
    worksheet_count = fields.Integer(compute='_compute_worksheet_count')

    @api.onchange('point_id')
    def _onchange_point_id(self):
        super()._onchange_point_id()
        if self.point_id and self.point_id.test_type == 'worksheet':
            self.worksheet_template_id = self.point_id.worksheet_template_id

    @api.depends('worksheet_template_id')
    def _compute_worksheet_count(self):
        for rec in self:
            rec.worksheet_count = rec.worksheet_template_id and rec.env[rec.worksheet_template_id.model_id.sudo().model].search_count([('x_quality_check_id', '=', rec.id)]) or 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'point_id' in vals and not vals.get('worksheet_template_id'):
                point = self.env['quality.point'].browse(vals['point_id'])
                if point.test_type == 'worksheet':
                    vals['worksheet_template_id'] = point.worksheet_template_id.id
        return super().create(vals_list)

    def action_quality_worksheet(self):
        action = self.worksheet_template_id.action_id.sudo().read()[0]
        worksheet = self.env[self.worksheet_template_id.model_id.sudo().model].search([('x_quality_check_id', '=', self.id)])
        context = literal_eval(action.get('context', '{}'))
        action.update({
            'res_id': worksheet.id if worksheet else False,
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                **context,
                'edit': True,
                'default_x_quality_check_id': self.id,
                'form_view_initial_mode': 'edit',
            },
        })
        return action

    def action_worksheet_check(self):
        self.ensure_one()
        if self.worksheet_count == 0:
            raise UserError(_("Please fill in the worksheet."))
        else:
            domain = literal_eval(self.point_id.worksheet_success_conditions or '[]')
            model = self.env[self.worksheet_template_id.model_id.model]
            if model.search(expression.AND([domain, [('x_quality_check_id', '=', self.id)]])):
                self.do_pass()
                return self.action_generate_next_window()
            else:
                # TODO: Write fail message ?
                self.do_fail()
                if self.quality_state == 'fail' and self._is_pass_fail_applicable() and (self.failure_message or self.warning_message):
                    return self.show_failure_message()
                return self.action_generate_next_window()

    def action_worksheet_discard(self):
        check_ids = self.env.context.get('check_ids')
        if check_ids:
            return self.env['quality.check'].search([('id', 'in', check_ids)]).action_open_quality_check_wizard(
                current_check_id=self.env.context.get('current_check_id')
            )
        return {'type': 'ir.actions.act_window_close'}

    def action_generate_next_window(self):
        check_ids = self.env.context.get('check_ids')
        current_check_id = self.env.context.get('current_check_id')
        if check_ids and current_check_id:
            position_next_check_id = check_ids.index(current_check_id) + 1
            if position_next_check_id < len(check_ids):
                next_check_id = check_ids[position_next_check_id]
                return self.env['quality.check'].browse(check_ids).action_open_quality_check_wizard(next_check_id)
        return {'type': 'ir.actions.act_window_close'}

    def correct_worksheet(self):
        self.ensure_one()
        if self.worksheet_template_id:
            action = self.action_quality_worksheet()
            action['name'] = "%s : %s %s" % (self.product_id.display_name, self.name, self.title or '')
            action['context']['hide_check_button'] = False
            return action

    def _is_pass_fail_applicable(self):
        return self.test_type == 'worksheet' and True or super()._is_pass_fail_applicable()

    def show_failure_message(self):
        return {
            'name': _('Quality Check Failed'),
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'views': [(self.env.ref('quality_control_worksheet.quality_check_view_form_failure_worksheet').id, 'form')],
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context,
        }
