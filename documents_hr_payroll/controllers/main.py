# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.sign.controllers.main import Sign
from odoo.http import request


class SignContract(Sign):

    @http.route([
        '/sign/sign/<int:sign_request_id>/<token>',
        '/sign/sign/<int:sign_request_id>/<token>/<sms_token>'
        ], type='json', auth='public')
    def sign(self, sign_request_id, token, sms_token=False, signature=None, **kwargs):
        result = super().sign(sign_request_id, token, sms_token=sms_token, signature=signature, **kwargs)
        request_item = request.env['sign.request.item'].sudo().search([('access_token', '=', token)])
        contract = request.env['hr.contract'].sudo().with_context(active_test=False).search([
            ('sign_request_ids', 'in', request_item.sign_request_id.ids)])
        employee_role = request.env.ref('sign.sign_item_role_employee')
        if contract and \
                contract.company_id.documents_payroll_folder_id and \
                contract.company_id.documents_hr_settings and \
                all(state == 'completed' for state in request_item.sign_request_id.request_item_ids.mapped('state')) and \
                employee_role in request_item.sign_request_id.request_item_ids.role_id:
            request_item.sign_request_id._generate_completed_document()

            employee_request_item = request_item.sign_request_id.request_item_ids.filtered(
                lambda i: i.role_id == employee_role)
            employee_partner = employee_request_item.partner_id

            user = request.env['res.users'].search([('partner_id', '=', employee_partner.id)], limit=1)
            if not user:
                employee = request.env['hr.employee'].search([('address_home_id', '=', employee_partner.id)])
                user = employee.user_id

            request.env['documents.document'].create({
                'owner_id': user.id,
                'datas': request_item.sign_request_id.completed_document,
                'name': request_item.sign_request_id.display_name,
                'folder_id': contract.company_id.documents_payroll_folder_id.id,
                'res_model': 'hr.payslip',  # Security Restriction to payroll managers
            })
        return result
