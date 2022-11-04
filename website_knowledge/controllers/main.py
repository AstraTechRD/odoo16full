# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.knowledge.controllers.main import KnowledgeController


class KnowledgeWebsiteController(KnowledgeController):

    # Override routes to display articles to public users
    @http.route('/knowledge/article/<int:article_id>', type='http', auth='public', website=True, sitemap=False)
    def redirect_to_article(self, **kwargs):
        if request.env.user._is_public():
            article = request.env['knowledge.article'].sudo().browse(kwargs['article_id'])
            if not article.exists():
                raise werkzeug.exceptions.NotFound()
            if not article.website_published:
                # public users can't access articles that are not published, let them login first
                return request.redirect('/web/login?redirect=/knowledge/article/%s' % kwargs['article_id'])
        return super().redirect_to_article(**kwargs)

    @http.route('/knowledge/home', type='http', auth='public', website=True, sitemap=False)
    def access_knowledge_home(self):
        return super().access_knowledge_home()

    @http.route('/knowledge/tree_panel/children', type='json', auth='public', website=True, sitemap=False)
    def get_tree_panel_children(self, parent_id):
        return super().get_tree_panel_children(parent_id)
