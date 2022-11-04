import odoo
from odoo import http

from odoo.http import request
from odoo.addons.web_studio.controllers import main

class WebStudioController(main.WebStudioController):

    @http.route('/web_studio/edit_view', type='json', auth='user')
    def edit_view(self, view_id, studio_view_arch, operations=None, model=None):
        action = super(WebStudioController, self).edit_view(view_id, studio_view_arch, operations)
        model = request.env['ir.ui.view'].browse(view_id).model
        worksheet_template_to_change = request.env['worksheet.template'].sudo().search([('model_id', '=', model)])
        if worksheet_template_to_change:
            worksheet_template_to_change._generate_qweb_report_template()
        return action
