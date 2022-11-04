# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from datetime import datetime
from urllib.parse import quote
from werkzeug.urls import url_join
from urllib.parse import urlparse

from odoo import models, _
from odoo.exceptions import UserError


class SocialStreamLinkedIn(models.Model):
    _inherit = 'social.stream'

    def _apply_default_name(self):
        linkedin_streams = self.filtered(lambda s: s.media_id.media_type == 'linkedin')
        super(SocialStreamLinkedIn, (self - linkedin_streams))._apply_default_name()

        for stream in linkedin_streams:
            stream.write({'name': '%s: %s' % (stream.stream_type_id.name, stream.account_id.name)})

    def _fetch_stream_data(self):
        """Fetch stream data, return True if new data.

        We need to perform 2 HTTP requests. One to retrieve all the posts of
        the organization page and the other, in batch, to retrieve the
        statistics of all posts (there are 2 different endpoints)."""
        self.ensure_one()
        if self.media_id.media_type != 'linkedin':
            return super(SocialStreamLinkedIn, self)._fetch_stream_data()

        # retrieve post information
        if self.stream_type_id.stream_type != 'linkedin_company_post':
            raise UserError(_('Wrong stream type for "%s"', self.name))

        projection = '(paging,elements*(%s))' % self.env['social.media']._LINKEDIN_STREAM_POST_PROJECTION
        posts_endpoint = url_join(
            self.env['social.media']._LINKEDIN_ENDPOINT,
            'ugcPosts?authors=List(%s)' % quote(self.account_id.linkedin_account_urn))

        posts_response = requests.get(
            posts_endpoint, params={'q': 'authors', 'projection': projection, 'count': 100},
            headers=self.account_id._linkedin_bearer_headers(),
            timeout=5)

        if posts_response.status_code != 200 or 'elements' not in posts_response.json():
            self.sudo().account_id._action_disconnect_accounts(posts_response.json())
            return False

        linkedin_post_data = {
            stream_post_data.get('id'): self._prepare_linkedin_stream_post_values(stream_post_data)
            for stream_post_data in posts_response.json()['elements']
        }

        # retrieve post statistics
        stats_endpoint = url_join(
            self.env['social.media']._LINKEDIN_ENDPOINT,
            'socialActions?ids=List(%s)' % ','.join([quote(urn) for urn in linkedin_post_data]))
        stats_response = requests.get(stats_endpoint, params={'count': 100}, headers=self.account_id._linkedin_bearer_headers(), timeout=5).json()

        if 'results' in stats_response:
            for post_urn, post_data in stats_response['results'].items():
                linkedin_post_data[post_urn].update({
                    'linkedin_comments_count': post_data.get('commentsSummary', {}).get('totalFirstLevelComments', 0),
                    'linkedin_likes_count': post_data.get('likesSummary', {}).get('totalLikes', 0),
                })

        # create/update post values
        existing_post_urns = {
            stream_post.linkedin_post_urn: stream_post
            for stream_post in self.env['social.stream.post'].search([
                ('stream_id', '=', self.id),
                ('linkedin_post_urn', 'in', list(linkedin_post_data.keys()))])
        }

        post_to_create = []
        for post_urn in linkedin_post_data:
            if post_urn in existing_post_urns:
                existing_post_urns[post_urn].sudo().write(linkedin_post_data[post_urn])
            else:
                post_to_create.append(linkedin_post_data[post_urn])

        if post_to_create:
            self.env['social.stream.post'].sudo().create(post_to_create)

        return bool(post_to_create)

    def _format_linkedin_name(self, json_data):
        user_name = '%s %s' % (json_data.get('localizedLastName', ''), json_data.get('localizedFirstName', ''))
        return json_data.get('localizedName', user_name)

    def _prepare_linkedin_stream_post_values(self, data):
        medias = data.get('specificContent', {}).get('com.linkedin.ugc.ShareContent', {}).get('media', [])
        post_values = {
            'stream_id': self.id,
            'author_name': self._format_linkedin_name(data.get('author~', {})),
            'published_date': datetime.fromtimestamp(data.get('created', {}).get('time', 0) / 1000),
            'linkedin_post_urn': data.get('id'),
            'linkedin_author_urn': data.get('author'),
            'message': data.get('specificContent', {}).get('com.linkedin.ugc.ShareContent', {}).get('shareCommentary', {}).get('text'),
            'linkedin_author_image_url': self.account_id._extract_linkedin_picture_url(data.get('author~')),
            'stream_post_image_ids': [(5, 0)] + [(0, 0, image_value) for image_value in self._extract_linkedin_image(medias)],
        }
        post_values.update(self._extract_linkedin_article(medias))
        return post_values

    def _extract_linkedin_image(self, medias):
        return [
            {'image_url': self._enforce_url_scheme(media.get('originalUrl'))}
            for media in medias
            if media.get('originalUrl') and 'digitalmediaAsset' in media.get('media', '')
        ]

    def _extract_linkedin_article(self, medias):
        if not medias or 'article' not in medias[0].get('media', ''):
            return {}

        return {
            'link_title': medias[0].get('title', {}).get('text'),
            'link_description': medias[0].get('description', {}).get('text'),
            'link_image_url': self._enforce_url_scheme((medias[0].get('thumbnails') or [{}])[0].get('url')),
            'link_url': self._enforce_url_scheme(medias[0].get('originalUrl'))
        }

    def _enforce_url_scheme(self, url):
        """Some URLs doesn't starts by "https://". But if we use those bad URLs
        in a HTML link, it will redirect the user the actual website.
        That's why we need to fix those URLs.
        e.g.:
            <a href="www.bad_url.com"/>
        """
        if not url or urlparse(url).scheme:
            return url

        return 'https://%s' % url
