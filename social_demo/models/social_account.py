# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class DemoSocialAccount(models.Model):
    _inherit = 'social.account'

    def _compute_statistics(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_facebook(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_twitter(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_youtube(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _refresh_youtube_token(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_instagram(self):
        """ Overridden to bypass third-party API calls. """
        return

    def twitter_search_users(self, query):
        """ Returns some fake suggestions """
        res_partners = [
            self.env.ref('social_demo.res_partner_2', raise_if_not_found=False),
            self.env.ref('social_demo.res_partner_3', raise_if_not_found=False),
            self.env.ref('social_demo.res_partner_4', raise_if_not_found=False)
        ]
        return [{
            'name': res_partner.name,
            'profile_image_url_https': '/web/image/res.partner/%s/avatar_128' % res_partner.id,
            'screen_name': res_partner.name.replace(' ', '').lower(),
            'description': res_partner.website

        } for res_partner in res_partners if res_partner]
