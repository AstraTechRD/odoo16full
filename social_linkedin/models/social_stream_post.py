# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import requests
from urllib.parse import quote
from datetime import datetime
from werkzeug.urls import url_join

from odoo import models, fields


class SocialStreamPostLinkedIn(models.Model):
    _inherit = 'social.stream.post'

    linkedin_post_urn = fields.Char('LinkedIn post URN')
    linkedin_author_urn = fields.Char('LinkedIn author URN')
    linkedin_author_id = fields.Char('LinkedIn author ID', compute='_compute_linkedin_author_urn')
    linkedin_author_vanity_name = fields.Char('LinkedIn Vanity Name', help='Vanity name, used to generate a link to the author')
    linkedin_author_image_url = fields.Char('LinkedIn author image URL')

    linkedin_comments_count = fields.Integer('LinkedIn Comments')
    linkedin_likes_count = fields.Integer('LinkedIn Likes')

    def _compute_linkedin_author_urn(self):
        for post in self:
            if post.linkedin_author_urn:
                post.linkedin_author_id = post.linkedin_author_urn.split(':')[-1]
            else:
                post.linkedin_author_id = False

    def _compute_author_link(self):
        linkedin_posts = self._filter_by_media_types(['linkedin'])
        super(SocialStreamPostLinkedIn, (self - linkedin_posts))._compute_author_link()

        for post in linkedin_posts:
            if post.linkedin_author_urn:
                post.author_link = 'https://linkedin.com/company/%s' % post.linkedin_author_id
            else:
                post.author_link = False

    def _compute_post_link(self):
        linkedin_posts = self._filter_by_media_types(['linkedin'])
        super(SocialStreamPostLinkedIn, (self - linkedin_posts))._compute_post_link()

        for post in linkedin_posts:
            if post.linkedin_post_urn:
                post.post_link = 'https://www.linkedin.com/feed/update/%s' % post.linkedin_post_urn
            else:
                post.post_link = False

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _linkedin_comment_add(self, message, comment_urn=None):
        data = {
            'actor': self.account_id.linkedin_account_urn,
            'message': {
                'attributes': [],
                'text': message,
            },
        }

        if comment_urn:
            # we reply yo an existing comment
            data['parentComment'] = comment_urn

        response = requests.post(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT,
                     'socialActions/%s/comments' % quote(self.linkedin_post_urn)),
            params={'projection': '(%s)' % self.env['social.media']._LINKEDIN_COMMENT_PROJECTION},
            json=data,
            headers=self.account_id._linkedin_bearer_headers(),
            timeout=5).json()

        if 'created' not in response:
            self.sudo().account_id._action_disconnect_accounts(response)
            return {}

        return self._linkedin_format_comment(response)

    def _linkedin_comment_delete(self, comment_urn):
        comment_id = re.search(r'urn:li:comment:\(urn:li:activity:\w+,(\w+)\)', comment_urn).group(1)
        endpoint = url_join(
            self.env['social.media']._LINKEDIN_ENDPOINT,
            'socialActions/%s/comments/%s' % (quote(self.linkedin_post_urn), quote(comment_id)))

        response = requests.request(
            'DELETE', endpoint, params={'actor': self.account_id.linkedin_account_urn},
            headers=self.account_id._linkedin_bearer_headers(),
            timeout=5)

        if response.status_code != 204:
            self.sudo().account_id._action_disconnect_accounts(response.json())

    def _linkedin_comment_fetch(self, comment_urn=None, offset=0, count=20):
        """Retrieve comments on a LinkedIn element.

        :param element_urn: URN of the element (UGC Post or Comment) on which we want to retrieve comments
            If no specified, retrieve comments on the current post
        :param offset: Used to scroll over the comments, position of the first retrieved comment
        :param count: Number of comments returned
        """
        element_urn = comment_urn or self.linkedin_post_urn

        response = requests.get(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'socialActions/%s/comments/' % quote(element_urn)),
            params={
                'start': offset,
                'count': count,
                'projection': '(paging,elements*(%s))' % self.env['social.media']._LINKEDIN_COMMENT_PROJECTION
            },
            headers=self.account_id._linkedin_bearer_headers(),
            timeout=5).json()

        if 'elements' not in response:
            self.sudo().account_id._action_disconnect_accounts(response)

        comments = [self._linkedin_format_comment(comment) for comment in response.get('elements', [])]
        if 'comment' in element_urn:
            # replies on comments should be sorted chronologically
            comments = comments[::-1]

        return {
            'postAuthorImage': self.linkedin_author_image_url,
            'currentUserUrn': self.account_id.linkedin_account_urn,
            'accountId': self.account_id.id,
            'comments': comments,
            'offset': offset + count,
            'summary': {'total_count': response.get('paging', {}).get('total', 0)},
        }

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _linkedin_format_comment(self, json_data):
        """Formats a comment returned by the LinkedIn API to a dict that will be interpreted by our frontend."""
        data = {
            'id': json_data.get('$URN'),
            'from': {
                'id': json_data.get('created', {}).get('actor'),
                'name': self.stream_id._format_linkedin_name(json_data.get('created', {}).get('actor~')),
                'authorUrn': json_data.get('created', {}).get('actor'),
                'picture': self.account_id._extract_linkedin_picture_url(json_data.get('created', {}).get('actor~')),
                'vanityName': json_data.get('created', {}).get('actor~').get('vanityName'),
                'isOrganization': 'organization' in json_data.get('created', {}).get('actor', ''),
            },
            'message': json_data.get('message', {}).get('text', ''),
            'created_time': json_data.get('created', {}).get('time', 0),
            'formatted_created_time': self.env['social.stream.post']._format_published_date(
                datetime.fromtimestamp(json_data.get('created', {}).get('time', 0) / 1000)),
            'likes': {
                'summary': {
                    'total_count': json_data.get('likesSummary', {}).get('totalLikes', 0),
                    'can_like': False,
                    'has_liked': json_data.get('likesSummary', {}).get('likedByCurrentUser', 0),
                }
            },
        }

        sub_comments_count = json_data.get('commentsSummary', {}).get('totalFirstLevelComments', 0)
        data['comments'] = {
            'data': {
                'length': sub_comments_count,
                'parentUrn': json_data.get('$URN'),
            } if sub_comments_count else []
        }

        return data

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'linkedin' and self.linkedin_post_urn:
            return self.env['social.live.post'].search(
                [('linkedin_post_id', '=', self.linkedin_post_urn)], limit=1
            ).post_id
        else:
            return super(SocialStreamPostLinkedIn, self)._fetch_matching_post()
