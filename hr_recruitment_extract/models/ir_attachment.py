# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def register_as_main_attachment(self, force=True):
        super().register_as_main_attachment(force=force)

        if self.res_model == 'hr.applicant' and self.env.company.recruitment_extract_show_ocr_option_selection == 'auto_send':
            applicant = self.env['hr.applicant'].browse(self.res_id).exists()
            if applicant and applicant.extract_can_show_send_button:
                applicant.action_manual_send_for_digitization()
