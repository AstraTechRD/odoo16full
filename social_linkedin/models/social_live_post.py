# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from urllib.parse import quote
from werkzeug.urls import url_join

from odoo import models, fields, tools, _
from odoo.exceptions import UserError


class SocialLivePostLinkedin(models.Model):
    _inherit = 'social.live.post'

    linkedin_post_id = fields.Char('Actual LinkedIn ID of the post')

    def _compute_live_post_link(self):
        linkedin_live_posts = self._filter_by_media_types(['linkedin']).filtered(lambda post: post.state == 'posted')
        super(SocialLivePostLinkedin, (self - linkedin_live_posts))._compute_live_post_link()

        for post in linkedin_live_posts:
            post.live_post_link = 'https://www.linkedin.com/feed/update/%s' % post.linkedin_post_id

    def _refresh_statistics(self):
        super(SocialLivePostLinkedin, self)._refresh_statistics()
        accounts = self.env['social.account'].search([('media_type', '=', 'linkedin')])

        for account in accounts:
            linkedin_post_ids = self.env['social.live.post'].sudo().search(
                [('account_id', '=', account.id), ('linkedin_post_id', '!=', False)],
                order='create_date DESC', limit=1000
            )
            if not linkedin_post_ids:
                continue

            linkedin_post_ids = {post.linkedin_post_id: post for post in linkedin_post_ids}

            session = requests.Session()

            # The LinkedIn API limit the query parameters to 4KB
            # An LinkedIn URN is approximatively 40 characters
            # So we keep a big margin and we split over 50 LinkedIn posts
            for batch_linkedin_post_ids in tools.split_every(50, linkedin_post_ids):
                endpoint = url_join(
                    self.env['social.media']._LINKEDIN_ENDPOINT,
                    'organizationalEntityShareStatistics?shares=List(%s)' % ','.join(map(quote, batch_linkedin_post_ids)))

                response = session.get(
                    endpoint, params={'q': 'organizationalEntity', 'organizationalEntity': account.linkedin_account_urn, 'count': 50},
                    headers=account._linkedin_bearer_headers(), timeout=10)

                if response.status_code != 200 or 'elements' not in response.json():
                    account._action_disconnect_accounts(response.json())
                    break

                for stats in response.json()['elements']:
                    urn = stats.get('share')
                    stats = stats.get('totalShareStatistics')

                    if not urn or not stats or urn not in batch_linkedin_post_ids:
                        continue

                    linkedin_post_ids[urn].update({
                        'engagement': stats.get('likeCount', 0) + stats.get('commentCount', 0) + stats.get('shareCount', 0)
                    })

    def _post(self):
        linkedin_live_posts = self._filter_by_media_types(['linkedin'])
        super(SocialLivePostLinkedin, (self - linkedin_live_posts))._post()

        linkedin_live_posts._post_linkedin()

    def _post_linkedin(self):
        for live_post in self:
            url_in_message = self.env['social.post']._extract_url_from_message(live_post.message)

            share_content = {
                "shareCommentary": {
                    "text": live_post.message
                },
                "shareMediaCategory": "NONE"
            }

            if live_post.post_id.image_ids:
                try:
                    images_urn = [
                        self._linkedin_upload_image(live_post.account_id, image_id)
                        for image_id in live_post.post_id.image_ids
                    ]
                except UserError as e:
                    live_post.write({
                        'state': 'failed',
                        'failure_reason': e.name
                    })
                    continue

                share_content.update({
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "media": image_urn
                    } for image_urn in images_urn]
                })
            elif url_in_message:
                share_content.update({
                    "shareMediaCategory": "ARTICLE",
                    "media": [{
                        "status": "READY",
                        "originalUrl": url_in_message
                    }]
                })

            data = {
                "author": live_post.account_id.linkedin_account_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": share_content
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            response = requests.post(
                url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'ugcPosts'),
                headers=live_post.account_id._linkedin_bearer_headers(),
                json=data, timeout=5).json()

            response_id = response.get('id')
            values = {
                'state': 'posted' if response_id else 'failed',
                'failure_reason': False
            }
            if response_id:
                values['linkedin_post_id'] = response_id
            else:
                values['failure_reason'] = response.get('message', 'unknown')

            if response.get('serviceErrorCode') == 65600:
                # Invalid access token
                self.account_id._action_disconnect_accounts(response)

            live_post.write(values)

    def _linkedin_upload_image(self, account_id, image_id):
        # 1 - Register your image to be uploaded
        data = {
            "registerUploadRequest": {
                "recipes": [
                    "urn:li:digitalmediaRecipe:feedshare-image"
                ],
                "owner": account_id.linkedin_account_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }

        response = requests.post(
                url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'assets?action=registerUpload'),
                headers=account_id._linkedin_bearer_headers(),
                json=data, timeout=5).json()

        if 'value' not in response or 'asset' not in response['value']:
            raise UserError(_("We could not upload your image, try reducing its size and posting it again (error: Failed during upload registering)."))

        # 2 - Upload image binary file
        upload_url = response['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        image_urn = response['value']['asset']

        data = image_id.with_context(bin_size=False).raw

        headers = account_id._linkedin_bearer_headers()
        headers['Content-Type'] = 'application/octet-stream'

        response = requests.request('POST', upload_url, data=data, headers=headers, timeout=15)

        if response.status_code != 201:
            raise UserError(_("We could not upload your image, try reducing its size and posting it again."))

        return image_urn
