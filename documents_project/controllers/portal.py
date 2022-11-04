# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal


class DocumentsProjectCustomerPortal(CustomerPortal):
    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        if project.use_documents and project.sudo().shared_document_count:
            groupby = 'project'
        return super()._project_get_page_view_values(project, access_token, page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search, search_in=search_in, groupby=groupby, **kwargs)
