# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class HrRecruitmentExtractController(http.Controller):
    @http.route('/hr_recruitment_extract/request_done/<int:extract_remote_id>', type='http', auth='public', csrf=False)
    def request_done(self, extract_remote_id):
        """ This webhook is called when the extraction server is done processing a request."""
        applicant_to_update = request.env['hr.applicant'].sudo().search([
            ('extract_remote_id', '=', extract_remote_id),
            ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']),
            ('is_first_stage', '=', True)])
        for applicant in applicant_to_update:
            applicant._check_ocr_status()
        return 'OK'
