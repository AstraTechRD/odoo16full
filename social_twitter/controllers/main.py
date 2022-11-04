# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import requests

from odoo import http, _
from odoo.addons.social.controllers.main import SocialController
from odoo.addons.social.controllers.main import SocialValidationException
from odoo.exceptions import UserError
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_encode, url_join


class SocialTwitterController(SocialController):
    # ========================================================
    # Accounts management
    # ========================================================

    @http.route('/social_twitter/callback', type='http', auth='user')
    def social_twitter_account_callback(self, oauth_token=None, oauth_verifier=None, iap_twitter_consumer_key=None, **kw):
        """ When we add accounts though IAP, we copy the 'iap_twitter_consumer_key' to our media's twitter_consumer_key.
        This allows preparing the signature process and the information is not sensitive so we can take advantage of it. """
        if not request.env.user.has_group('social.group_social_manager'):
            return request.render('social.social_http_error_view',
                                  {'error_message': _('Unauthorized. Please contact your administrator.')})

        if not kw.get('denied'):
            if not oauth_token or not oauth_verifier:
                return request.render('social.social_http_error_view',
                                      {'error_message': _('Twitter did not provide a valid access token.')})

            if iap_twitter_consumer_key:
                request.env['ir.config_parameter'].sudo().set_param('social.twitter_consumer_key', iap_twitter_consumer_key)

            media = request.env['social.media'].search([('media_type', '=', 'twitter')], limit=1)

            try:
                self._twitter_create_accounts(oauth_token, oauth_verifier, media)
            except SocialValidationException as e:
                return request.render('social.social_http_error_view',
                                      {'error_message': str(e)})

        url_params = {
            'action': request.env.ref('social.action_social_stream_post').id,
            'view_type': 'kanban',
            'model': 'social.stream.post',
        }

        url = '/web?#%s' % url_encode(url_params)
        return request.redirect(url)

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    @http.route('/social_twitter/<int:stream_id>/comment', type='http', methods=['POST'])
    def social_twitter_comment(self, stream_id=None, stream_post_id=None, comment_id=None,
                               message=None, answering_to=None, **kwargs):
        """Send a Tweet as an answer of an other Tweet.

        When answering to a Tweet, its author will be automatically mention in the answer
        so our Tweet will be correctly displayed as an answer on Tweeter.

        All other mention will be removed to avoid spam abuse.

        :param stream_id: Id of the original <social.stream>
        :param stream_post_id: Id of the original <social.stream.post>
        :param comment_id: We if reply to a "comment" (aka tweet), this is the Tweeter id
        :param message: Text message to send
        :param answering_to: If we reply to a "comment", this is the screen name of the
            "comment" author (it will be automatically mention in the answer)
        """
        stream = request.env['social.stream'].browse(stream_id)
        if not stream.exists() or stream.media_id.media_type != 'twitter':
            raise Forbidden()

        stream_post = self._get_social_stream_post(stream_post_id, 'twitter')
        answering_to = answering_to if comment_id else stream_post.twitter_screen_name

        # Add mention in the message if not present and remove other mentions.
        # This is needed when answering to a tweet, otherwise the new tweet will not be
        # displayed as a response on Twitter.
        message = request.env["social.live.post"]._remove_mentions(message, [answering_to])
        if f'@{answering_to.lower()}' not in message.lower():
            message = f"@{answering_to} {message}"

        return json.dumps(stream_post._twitter_comment_add(stream, comment_id, message))

    @http.route('/social_twitter/delete_tweet', type='json')
    def social_twitter_delete_tweet(self, stream_post_id, comment_id):
        stream_post = self._get_social_stream_post(stream_post_id, 'twitter')
        return stream_post._twitter_tweet_delete(comment_id)

    @http.route('/social_twitter/get_comments', type='json')
    def social_twitter_get_comments(self, stream_post_id, page=1):
        stream_post = self._get_social_stream_post(stream_post_id, 'twitter')
        return stream_post._twitter_comment_fetch(page)

    @http.route('/social_twitter/<int:stream_id>/like_tweet', type='json')
    def social_twitter_like_tweet(self, stream_id, tweet_id, like):
        stream = request.env['social.stream'].browse(stream_id)
        if not stream.exists() or stream.media_id.media_type != 'twitter':
            raise Forbidden()

        return request.env['social.stream.post']._twitter_tweet_like(stream, tweet_id, like)

    @http.route('/social_twitter/<int:stream_id>/retweet', type='json', auth='user')
    def social_twitter_do_retweet(self, stream_id, tweet_id):
        """
        :param string stream_id: ID of the stream
        :param string tweet_id: ID of the tweet generated by Twitter
        """
        if not stream_id or not tweet_id:
            raise NotFound()
        tweet = request.env['social.stream.post'].search([
            ('twitter_tweet_id', '=', tweet_id),
            ('stream_id', '=', stream_id)
        ], limit=1)
        if not tweet:
            raise NotFound()
        try:
            return tweet._twitter_do_retweet()
        except UserError as error:
            return json.dumps({
                'error': str(error)
            })

    @http.route('/social_twitter/<int:stream_id>/unretweet', type='json', auth='user')
    def social_twitter_undo_retweet(self, stream_id, tweet_id):
        """
        :param string stream_id: ID of the stream
        :param string tweet_id: ID of the tweet generated by Twitter
        """
        if not stream_id or not tweet_id:
            raise NotFound()
        tweet = request.env['social.stream.post'].search([
            ('twitter_tweet_id', '=', tweet_id),
            ('stream_id', '=', stream_id)
        ], limit=1)
        if not tweet.exists():
            return NotFound()
        try:
            return tweet._twitter_undo_retweet()
        except UserError as error:
            return json.dumps({
                'error': str(error)
            })

    @http.route('/social_twitter/<int:stream_id>/quote', type='http', methods=['POST'], auth='user')
    def social_twitter_tweet_quote(self, stream_id, tweet_id, message):
        """
        :param string stream: ID of the stream
        :param string tweet_id: ID of the tweet generated by Twitter
        :param string message: Body of the quote
        """
        if not stream_id or not tweet_id:
            return NotFound()
        tweet = request.env['social.stream.post'].search([
            ('twitter_tweet_id', '=', tweet_id),
            ('stream_id', '=', stream_id)
        ], limit=1)
        if not tweet:
            return NotFound()
        files = request.httprequest.files.getlist('attachment')
        # Extract all attachments from the request:
        attachment = files[0] if files and files[0] else None
        try:
            return json.dumps(tweet._twitter_tweet_quote(message, attachment))
        except UserError as error:
            return json.dumps({
                'error': str(error)
            })

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _twitter_create_accounts(self, oauth_token, oauth_verifier, media):
        twitter_consumer_key = request.env['ir.config_parameter'].sudo().get_param('social.twitter_consumer_key')

        twitter_access_token_url = url_join(request.env['social.media']._TWITTER_ENDPOINT, "oauth/access_token")
        response = requests.post(twitter_access_token_url,
            data={
                'oauth_consumer_key': twitter_consumer_key,
                'oauth_token': oauth_token,
                'oauth_verifier': oauth_verifier
            },
            timeout=5
        )

        if response.status_code != 200:
            raise SocialValidationException(_('Twitter did not provide a valid access token or it may have expired.'))

        response_values = {
            response_value.split('=')[0]: response_value.split('=')[1]
            for response_value in response.text.split('&')
        }

        existing_account = request.env['social.account'].sudo().with_context(active_test=False).search([
            ('media_id', '=', media.id),
            ('twitter_user_id', '=', response_values['user_id'])
        ])

        error_message = existing_account._get_multi_company_error_message()
        if error_message:
            raise SocialValidationException(error_message)

        if existing_account:
            existing_account.write({
                'active': True,
                'is_media_disconnected': False,
                'social_account_handle': response_values['screen_name'],
                'twitter_oauth_token': response_values['oauth_token'],
                'twitter_oauth_token_secret': response_values['oauth_token_secret']
            })
        else:
            twitter_account_information = self._twitter_get_account_information(
                media,
                response_values['oauth_token'],
                response_values['oauth_token_secret'],
                response_values['screen_name']
            )

            request.env['social.account'].create({
                'media_id': media.id,
                'name': twitter_account_information['name'],
                'twitter_user_id': response_values['user_id'],
                'social_account_handle': response_values['screen_name'],
                'twitter_oauth_token': response_values['oauth_token'],
                'twitter_oauth_token_secret': response_values['oauth_token_secret'],
                'image': base64.b64encode(requests.get(twitter_account_information['profile_image_url_https'], timeout=10).content)
            })

    def _twitter_get_account_information(self, media, oauth_token, oauth_token_secret, screen_name):
        twitter_account_info_url = url_join(request.env['social.media']._TWITTER_ENDPOINT, "/1.1/users/show.json")

        headers = media._get_twitter_oauth_header(
            twitter_account_info_url,
            headers={
                'oauth_token': oauth_token,
                'oauth_token_secret': oauth_token_secret,
            },
            params={'screen_name': screen_name},
            method='GET'
        )

        response = requests.get(twitter_account_info_url,
            params={
                'screen_name': screen_name
            },
            headers=headers,
            timeout=5
        )
        return response.json()
