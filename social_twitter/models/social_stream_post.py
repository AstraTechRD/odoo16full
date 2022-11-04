# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import _, api, models, fields
from odoo.exceptions import UserError
from odoo.http import request
from werkzeug.urls import url_join


class SocialStreamPostTwitter(models.Model):
    _inherit = 'social.stream.post'

    twitter_tweet_id = fields.Char('Twitter Tweet ID', index=True)
    twitter_author_id = fields.Char('Twitter Author ID')
    twitter_screen_name = fields.Char('Twitter Screen Name')
    twitter_profile_image_url = fields.Char('Twitter Profile Image URL')
    twitter_likes_count = fields.Integer('Twitter Likes')
    twitter_user_likes = fields.Boolean('Twitter User Likes')
    twitter_comments_count = fields.Integer('Twitter Comments')
    twitter_retweet_count = fields.Integer('Re-tweets')

    twitter_retweeted_tweet_id_str = fields.Char('Twitter Retweet ID')
    twitter_can_retweet = fields.Boolean(compute='_compute_twitter_can_retweet')
    twitter_quoted_tweet_id_str = fields.Char('Twitter Quoted Tweet ID')
    twitter_quoted_tweet_message = fields.Text('Quoted tweet message')
    twitter_quoted_tweet_author_name = fields.Char('Quoted tweet author Name')
    twitter_quoted_tweet_author_link = fields.Char('Quoted tweet author Link')
    twitter_quoted_tweet_profile_image_url = fields.Char('Quoted tweet profile image URL')

    _sql_constraints = [
        ('tweet_uniq', 'UNIQUE (twitter_tweet_id, stream_id)', 'You can not store two times the same tweet on the same stream!')
    ]

    def _compute_author_link(self):
        twitter_posts = self._filter_by_media_types(['twitter'])
        super(SocialStreamPostTwitter, (self - twitter_posts))._compute_author_link()

        for post in twitter_posts:
            post.author_link = 'https://twitter.com/intent/user?user_id=%s' % post.twitter_author_id

    def _compute_post_link(self):
        twitter_posts = self._filter_by_media_types(['twitter'])
        super(SocialStreamPostTwitter, (self - twitter_posts))._compute_post_link()

        for post in twitter_posts:
            post.post_link = 'https://www.twitter.com/%s/statuses/%s' % (post.twitter_author_id, post.twitter_tweet_id)

    @api.depends('twitter_retweeted_tweet_id_str', 'twitter_tweet_id')
    def _compute_twitter_can_retweet(self):
        tweets = self.filtered(lambda post: post.twitter_tweet_id)
        (self - tweets).twitter_can_retweet = False
        if not tweets:
            return

        tweet_ids = set(tweets.mapped('twitter_tweet_id')) | set(tweets.mapped('twitter_retweeted_tweet_id_str'))
        twitter_author_ids = set(tweets.stream_id.account_id.mapped('twitter_user_id'))

        potential_retweets = self.search([
            ('twitter_author_id', 'in', list(twitter_author_ids)),
            '|',
                ('twitter_tweet_id', 'in', list(tweet_ids)),
                ('twitter_retweeted_tweet_id_str', 'in', list(tweet_ids)),
        ])

        for tweet in tweets:
            account = tweet.stream_id.account_id
            if tweet.twitter_retweeted_tweet_id_str and tweet.twitter_author_id == account.twitter_user_id:
                # If the tweet is a retweet and has been posted with the given account, the user will not
                # be allowed to retweet the tweet.
                tweet.twitter_can_retweet = False
                continue
            # Otherwise, the user will be allowed to retweet the tweet if there does not exist a retweet
            # of that tweet posted with the given account.
            original_tweet_id = tweet.twitter_retweeted_tweet_id_str or tweet.twitter_tweet_id
            tweet.twitter_can_retweet = not any(
                current.twitter_retweeted_tweet_id_str == original_tweet_id and \
                current.twitter_author_id == account.twitter_user_id for current in potential_retweets
            )

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _twitter_comment_add(self, stream, comment_id, message):
        self.ensure_one()
        tweet_id = comment_id or self.twitter_tweet_id
        params = {
            'status': message,
            'in_reply_to_status_id': tweet_id,
            'tweet_mode': 'extended',
        }

        attachment = None
        files = request.httprequest.files.getlist('attachment')
        if files and files[0]:
            attachment = files[0]

        if attachment:
            images_attachments_ids = stream.account_id._format_bytes_to_images_twitter(attachment)
            if images_attachments_ids:
                params['media_ids'] = ','.join(images_attachments_ids)

        post_endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, "/1.1/statuses/update.json")
        headers = stream.account_id._get_twitter_oauth_header(
            post_endpoint_url,
            params=params
        )
        result = requests.post(
            post_endpoint_url,
            data=params,
            headers=headers,
            timeout=5
        )

        if result.ok:
            return self.env['social.media']._format_tweet(result.json())

        # Parse the code error returned by the Twitter API.
        errors = result.json().get('errors')
        if errors and errors[0].get('code'):
            ERROR_MESSAGES = {
                170: _("The tweet is empty. Add a message and try posting again."),
                187: _("Looks like this Tweet is a duplicate. Edit its content and try posting again."),
            }
            message = errors[0].get('message') or _("Code %i", errors[0].get('code'))
            return {
                'error': ERROR_MESSAGES.get(
                    errors[0]['code'],
                    _("An error occurred (%s)", message))
            }

        return {'error': _('Unknown error')}

    def _twitter_comment_fetch(self, page=1):
        """ As of today (07/2019) Twitter does not provide an endpoint to get the 'answers' to a tweet.
        This is why we have to use a quite dirty workaround to try and recover that information.

        Basically, what we do if fetch all tweets that are:
            - directed to our user ('to': twitter_screen_name)
            - are after out tweet_id ('since_id': twitter_tweet_id)

        We accumulate up to 1000 tweets matching that rule, 100 at a time (API limit).

        Then, it gets even more complicated, because the first result batch does not include tweets
        made by our use (twitter_screen_name) as replies to their own root tweet.
        That's why we have to do a second request to get the tweets FROM out user, after the root tweet.
        We also accumulate up to 1000 tweets.

        The two results are merged together (up to 2000 tweets).

        Then we filter these tweets to search for those that are replies to our root tweet
        ('in_reply_to_status_id_str') == self.twitter_tweet_id.
        And we also keep tweets that are replies to replies to our root tweet (stay with me here).

        Needless to say this has to be modified as soon as Twitter provides some way to recover replies
        to a tweet. """

        self.ensure_one()

        search_query = {
            'to': self.twitter_screen_name,
            'since_id': self.twitter_tweet_id,
        }

        tweets_endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, "/1.1/search/tweets.json")
        query_params = {
            'tweet_mode': 'extended',
            'result_type': 'recent',
            'count': 100,
            'include_entities': True,
        }
        answer_results = self._accumulate_tweets(tweets_endpoint_url, query_params, search_query)

        search_query = {
            'since_id': self.twitter_tweet_id,
            'from': self.twitter_screen_name
        }
        self_tweets = self._accumulate_tweets(tweets_endpoint_url, query_params, search_query)
        self_tweets = [tweet for tweet in self_tweets if tweet.get('id_str') not in [answer_tweet.get('id_str') for answer_tweet in answer_results]]

        all_tweets = list(answer_results) + list(self_tweets)
        sorted_tweets = sorted(all_tweets, key=lambda tweet: tweet.get('created_at'))

        filtered_tweets = []
        for tweet in sorted_tweets:
            if tweet.get('in_reply_to_status_id_str') == self.twitter_tweet_id:
                filtered_tweets.append(self.env['social.media']._format_tweet(tweet))
            else:
                for i in range(len(filtered_tweets)):
                    tested_against = [filtered_tweets[i].get('id')]
                    if filtered_tweets[i].get('comments'):
                        tested_against += [answer_tweet['id'] for answer_tweet in filtered_tweets[i]['comments']['data']]
                    if tweet.get('in_reply_to_status_id_str') in tested_against:
                        filtered_tweets[i]['comments'] = filtered_tweets[i].get('comments', {'data': []})
                        filtered_tweets[i]['comments']['data'] += [self.env['social.media']._format_tweet(tweet)]

        filtered_tweets = self._add_comments_favorites(filtered_tweets)

        return {
            'comments': list(reversed(filtered_tweets))
        }

    def _twitter_tweet_delete(self, tweet_id):
        self.ensure_one()
        delete_endpoint = url_join(self.env['social.media']._TWITTER_ENDPOINT, ('/1.1/statuses/destroy/%s.json' % tweet_id))
        headers = self.stream_id.account_id._get_twitter_oauth_header(
            delete_endpoint
        )
        requests.post(
            delete_endpoint,
            headers=headers,
            timeout=5
        )

        return True

    def _twitter_tweet_like(self, stream, tweet_id, like):
        favorites_endpoint = url_join(self.env['social.media']._TWITTER_ENDPOINT, (
            '/1.1/favorites/create.json' if like else '/1.1/favorites/destroy.json'
        ))
        headers = stream.account_id._get_twitter_oauth_header(
            favorites_endpoint,
            params={'id': tweet_id}
        )
        requests.post(
            favorites_endpoint,
            data={'id': tweet_id},
            headers=headers,
            timeout=5
        )

        return True

    def _twitter_do_retweet(self):
        """ Creates a new retweet for the given stream post on Twitter. """
        if not self.twitter_can_retweet:
            raise UserError(_('A retweet already exists'))

        retweet_endpoint = url_join(self.env['social.media']._TWITTER_ENDPOINT, (
            '1.1/statuses/retweet/%s.json' % self.twitter_tweet_id
        ))

        account = self.stream_id.account_id
        headers = account._get_twitter_oauth_header(retweet_endpoint)
        result = requests.post(retweet_endpoint, headers=headers, timeout=5)

        if result.ok: # 200-series HTTP code
            return True
        elif result.status_code == 401:
            account.write({'is_media_disconnected': True})
            raise UserError(_('You are not authenticated'))

        errors = result.json().get('errors')
        if errors and errors[0].get('code'):
            raise UserError(errors[0].get('message') or _('Code %i', errors[0].get('code')))

        raise UserError(_('Unknown error'))

    def _twitter_undo_retweet(self):
        """ Deletes the retweet of the given stream post from Twitter """
        unretweet_endpoint = url_join(self.env['social.media']._TWITTER_ENDPOINT, (
            '1.1/statuses/unretweet/%s.json' % (self.twitter_tweet_id)
        ))

        account = self.stream_id.account_id
        headers = account._get_twitter_oauth_header(unretweet_endpoint)
        result = requests.post(unretweet_endpoint, headers=headers, timeout=5)

        if result.status_code == 401:
            account.write({'is_media_disconnected': True})
            raise UserError(_('You are not authenticated'))

        errors = result.json().get('errors')
        if errors and errors[0].get('code'):
            if errors[0].get('code') != 144:
                # Error code 144: 'No status found with that ID'
                # If the error code is 144, it means that the tweet has probably been deleted from Twitter.
                # In that case, we do not catch the error and we simply remove the tweet (see below).
                raise UserError(errors[0].get('message') or _('Code %i', errors[0].get('code')))

        retweets = self.search([
            ('twitter_author_id', '=', self.stream_id.account_id.twitter_user_id),
            ('twitter_retweeted_tweet_id_str', '=', self.twitter_retweeted_tweet_id_str or self.twitter_tweet_id),
        ])
        retweets.unlink()
        return True

    def _twitter_tweet_quote(self, message, attachment=None):
        """
        :param werkzeug.datastructures.FileStorage attachment:
        Creates a new quotes for the current stream post on Twitter.
        If the stream post does not have any message, a retweet will be created instead of a quote.
        """
        if not message:
            return self._twitter_do_retweet()

        params = {
            'status': message,
            'attachment_url': 'https://twitter.com/%s/status/%s' % (
                self.twitter_author_id,
                self.twitter_tweet_id
            )
        }

        account = self.stream_id.account_id
        if attachment:
            images_attachments_ids = account._format_bytes_to_images_twitter(attachment)
            if images_attachments_ids:
                params['media_ids'] = ','.join(images_attachments_ids)

        quote_endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, '/1.1/statuses/update.json')
        headers = account._get_twitter_oauth_header(quote_endpoint_url, params=params)
        result = requests.post(quote_endpoint_url, data=params, headers=headers, timeout=5)

        if result.ok: # 200-series HTTP code
            return True
        elif result.status_code == 401:
            account.write({'is_media_disconnected': True})
            raise UserError(_('You are not authenticated'))

        raise UserError(_('Unknown error'))

    # ========================================================
    # UTILITY / MISC
    # ========================================================

    def _add_comments_favorites(self, filtered_tweets):
        all_tweets_ids = []
        for tweet in filtered_tweets:
            all_tweets_ids.append(tweet.get('id'))
            if 'comments' in tweet:
                all_tweets_ids += [answer_tweet['id'] for answer_tweet in tweet['comments']['data']]

        favorites_by_id = self.stream_id._lookup_tweets(all_tweets_ids)

        for i in range(len(filtered_tweets)):
            looked_up_tweet = favorites_by_id.get(filtered_tweets[i]['id'], {'favorited': False})
            filtered_tweets[i]['user_likes'] = looked_up_tweet['favorited']

            if 'comments' in filtered_tweets[i]:
                for j in range(len(filtered_tweets[i]['comments']['data'])):
                    looked_up_tweet = favorites_by_id.get(filtered_tweets[i]['comments']['data'][j]['id'], {'favorited': False})
                    filtered_tweets[i]['comments']['data'][j]['user_likes'] = looked_up_tweet['favorited']

        return filtered_tweets

    def _accumulate_tweets(self, endpoint_url, query_params, search_query, query_count=1, force_max_id=None):
        self.ensure_one()

        copied_search_query = dict(search_query)
        if force_max_id:
            copied_search_query['max_id'] = force_max_id

        if 'max_id' in copied_search_query and int(copied_search_query['max_id']) < int(copied_search_query['since_id']):
            del copied_search_query['max_id']

        twitter_query_string = ''
        for key, value in copied_search_query.items():
            twitter_query_string += '%s:%s ' % (key, value)

        query_params['q'] = twitter_query_string

        headers = self.stream_id.account_id._get_twitter_oauth_header(
            endpoint_url,
            params=query_params,
            method='GET'
        )
        result = requests.get(
            endpoint_url,
            params=query_params,
            headers=headers,
            timeout=5
        )
        tweets = result.json().get('statuses')
        if query_count >= 10:
            return tweets
        elif not tweets:
            return []
        elif len(tweets) < 100:
            return tweets
        else:
            max_id = int(tweets[-1].get('id_str')) - 1
            if max_id < int(search_query['since_id']):
                return tweets
            return tweets + self._accumulate_tweets(
                endpoint_url,
                query_params,
                search_query,
                query_count=(query_count + 1),
                force_max_id=str(max_id)
            )

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'twitter' and self.twitter_tweet_id:
            return self.env['social.live.post'].search(
                [('twitter_tweet_id', '=', self.twitter_tweet_id)], limit=1
            ).post_id
        else:
            return super(SocialStreamPostTwitter, self)._fetch_matching_post()
