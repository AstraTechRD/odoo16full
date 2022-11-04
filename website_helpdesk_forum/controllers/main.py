# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route, request
from odoo.osv import expression
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk
from odoo.addons.website_forum.controllers.main import WebsiteForum


class WebsiteHelpdeskForum(WebsiteHelpdesk):

    def _format_search_results(self, search_type, records, options):
        if search_type != 'forum_posts_only':
            return super()._format_search_results(search_type, records, options)

        questions = records.mapped('parent_id') | records.filtered(lambda s: not s.parent_id)
        return [{
            'template': 'website_helpdesk_forum.search_result',
            'record': question,
            'score': question.views + question.vote_count + question.favourite_count,
            'url': '/forum/%s/%s' % (slug(question.forum_id), slug(question)),
            'icon': 'fa-comments',
        } for question in questions]

class WebsiteForumHelpdesk(WebsiteForum):

    @route('/helpdesk/<model("helpdesk.team"):team>/forums', type='http', auth="public", website=True, sitemap=True)
    def helpdesk_forums(self, team=None):
        if not team or not team.website_forum_ids:
            return request.redirect('/forum')
        domain = expression.AND([request.website.website_domain(), [('id', 'in', team.website_forum_ids.ids)]])
        forums = request.env['forum.forum'].search(domain)
        if len(forums) == 1:
            return request.redirect('/forum/%s' % slug(forums[0]), code=302)
        return request.render(self.get_template_xml_id(), {
            'forums': forums
        })

    def get_template_xml_id(self):
        return "website_helpdesk_forum.forum_all"
