# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class QualityCheckWizard(models.TransientModel):

    _inherit = 'quality.check.wizard'

    worksheet_template_id = fields.Many2one(related='current_check_id.worksheet_template_id')

    def do_worksheet(self):
        check = self.current_check_id
        action = check.action_quality_worksheet()
        action['name'] = "%s : %s %s" % (check.product_id.display_name, check.name, check.title or '')
        action['context'].update(
            hide_check_button=False,
            check_ids=self.check_ids.ids,
            current_check_id=check.id,
        )
        return action
