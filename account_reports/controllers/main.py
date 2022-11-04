# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.models import check_method_name
from odoo.http import content_disposition, request
from odoo.tools import html_escape

import json


class AccountReportController(http.Controller):

    @http.route('/account_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_report(self, options, file_generator, **kwargs):
        uid = request.uid
        options = json.loads(options)

        allowed_company_ids = [company_data['id'] for company_data in options.get('multi_company', [])]
        if not allowed_company_ids:
            company_str = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
            allowed_company_ids = [int(str_id) for str_id in company_str.split(',')]

        report = request.env['account.report'].with_user(uid).with_context(allowed_company_ids=allowed_company_ids).browse(options['report_id'])

        try:
            check_method_name(file_generator)
            generated_file_data = report.dispatch_report_action(options, file_generator)
            file_content = generated_file_data['file_content']
            file_type = generated_file_data['file_type']
            response_headers = self._get_response_headers(file_type, generated_file_data['file_name'], file_content)

            if file_type == 'xlsx':
                response = request.make_response(None, headers=response_headers)
                response.stream.write(file_content)
            else:
                response = request.make_response(file_content, headers=response_headers)

            if file_type == 'zip':
                # Adding direct_passthrough to the response and giving it a file
                # as content means that we will stream the content of the file to the user
                # Which will prevent having the whole file in memory
                response.direct_passthrough = True

            return response
        except Exception as e:
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

    def _get_response_headers(self, file_type, file_name, file_content):
        headers = [
            ('Content-Type', request.env['account.report'].get_export_mime_type(file_type)),
            ('Content-Disposition', content_disposition(file_name)),
        ]

        if file_type in ('xml', 'xaf', 'txt', 'csv', 'kvr', 'csv'):
            headers.append(('Content-Length', len(file_content)))

        return headers
