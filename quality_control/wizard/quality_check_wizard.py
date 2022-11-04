# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class QualityCheckWizard(models.TransientModel):
    _name = 'quality.check.wizard'
    _description = "Wizard for Quality Check Pop Up"

    check_ids = fields.Many2many('quality.check', required=True)
    current_check_id = fields.Many2one('quality.check', required=True)
    nb_checks = fields.Integer(compute='_compute_nb_checks')
    position_current_check = fields.Integer(compute='_compute_position')
    is_last_check = fields.Boolean(compute='_compute_position')

    # fields linked to the current_check_id
    name = fields.Char(related='current_check_id.name')
    title = fields.Char(related='current_check_id.title')
    product_id = fields.Many2one(related='current_check_id.product_id')
    lot_name = fields.Char(related='current_check_id.lot_name')
    lot_line_id = fields.Many2one(related='current_check_id.lot_line_id')
    qty_line = fields.Float(related='current_check_id.qty_line')
    qty_to_test = fields.Float(related='current_check_id.qty_to_test')
    qty_tested = fields.Float(related='current_check_id.qty_tested', readonly=False)
    measure = fields.Float(related='current_check_id.measure', readonly=False)
    measure_on = fields.Selection(related='current_check_id.measure_on')
    quality_state = fields.Selection(related='current_check_id.quality_state')
    test_type = fields.Char(related='current_check_id.test_type')
    norm_unit = fields.Char(related='current_check_id.norm_unit')
    picture = fields.Binary(related='current_check_id.picture', readonly=False)
    note = fields.Html(related='current_check_id.note', readonly=False)
    additional_note = fields.Text(related='current_check_id.additional_note', readonly=False)
    is_lot_tested_fractionally = fields.Boolean(related="current_check_id.is_lot_tested_fractionally")
    testing_percentage_within_lot = fields.Float(related="current_check_id.testing_percentage_within_lot")
    uom_id = fields.Many2one(related="current_check_id.uom_id")
    warning_message = fields.Text(related='current_check_id.warning_message')
    failure_message = fields.Html(related='current_check_id.failure_message')
    show_lot_text = fields.Boolean(related='current_check_id.show_lot_text')
    product_tracking = fields.Selection(related='current_check_id.product_tracking')

    @api.depends('current_check_id', 'check_ids')
    def _compute_nb_checks(self):
        for wz in self:
            wz.nb_checks = len(wz.check_ids)

    @api.depends('current_check_id', 'check_ids')
    def _compute_position(self):
        for wz in self:
            wz.position_current_check = wz.check_ids.ids.index(wz.current_check_id.id) + 1
            wz.is_last_check = False
            if wz.position_current_check == len(wz.check_ids):
                wz.is_last_check = True

    def do_measure(self):
        self.current_check_id.do_measure()
        if self.quality_state == 'fail' and self.current_check_id._is_pass_fail_applicable() and (self.failure_message or self.warning_message):
            return self.show_failure_message()
        return self.action_generate_next_window()

    def do_pass(self):
        if self.test_type == 'picture' and not self.picture:
            raise UserError('You must provide a picture before validating')
        self.current_check_id.do_pass()
        return self.action_generate_next_window()

    def do_fail(self):
        self.current_check_id.do_fail()
        if self.quality_state == 'fail' and self.current_check_id._is_pass_fail_applicable() and (self.failure_message or self.warning_message):
            return self.show_failure_message()
        return self.action_generate_next_window()

    def action_generate_next_window(self):
        if not self.is_last_check:
            action = self.env["ir.actions.actions"]._for_xml_id("quality_control.action_quality_check_wizard")
            action['context'] = dict(ast.literal_eval(action['context']))
            action['context'].update(
                self.env.context,
                default_current_check_id=self.check_ids[self.position_current_check].id
            )
            return action

    def action_generate_previous_window(self):
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.action_quality_check_wizard")
        action['context'] = dict(ast.literal_eval(action['context']))
        action['context'].update(
            self.env.context,
            default_current_check_id=self.check_ids[self.position_current_check - 2].id
        )
        return action

    def show_failure_message(self):
        return {
            'name': _('Quality Check Failed'),
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check.wizard',
            'views': [(self.env.ref('quality_control.quality_check_wizard_form_failure').id, 'form')],
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context,
        }

    def correct_measure(self):
        self.current_check_id.quality_state = 'none'
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.action_quality_check_wizard")
        action['context'] = dict(ast.literal_eval(action['context']))
        action['context'].update(
            self.env.context,
            default_check_ids=self.check_ids.ids,
            default_current_check_id=self.current_check_id.id,
        )
        return action
