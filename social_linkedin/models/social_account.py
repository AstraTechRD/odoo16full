# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import requests
from datetime import datetime, timedelta
from werkzeug.urls import url_join

from odoo import _, models, fields, api
from odoo.addons.social.controllers.main import SocialValidationException


class SocialAccountLinkedin(models.Model):
    _inherit = 'social.account'

    linkedin_account_urn = fields.Char('LinkedIn Account URN', readonly=True, help='LinkedIn Account URN')
    linkedin_account_id = fields.Char('LinkedIn Account ID', compute='_compute_linkedin_account_id')
    linkedin_access_token = fields.Char('LinkedIn access token', readonly=True, help='The access token is used to perform request to the REST API')

    @api.depends('linkedin_account_urn')
    def _compute_linkedin_account_id(self):
        """Depending on the used LinkedIn endpoint, we sometimes need the full URN, sometimes only the ID part.

        e.g.: "urn:li:person:12365" -> "12365"
        """
        for social_account in self:
            if social_account.linkedin_account_urn:
                social_account.linkedin_account_id = social_account.linkedin_account_urn.split(':')[-1]
            else:
                social_account.linkedin_account_id = False

    def _compute_stats_link(self):
        linkedin_accounts = self._filter_by_media_types(['linkedin'])
        super(SocialAccountLinkedin, (self - linkedin_accounts))._compute_stats_link()

        for account in linkedin_accounts:
            account.stats_link = 'https://www.linkedin.com/company/%s/admin/analytics/visitors/' % account.linkedin_account_id

    def _compute_statistics(self):
        linkedin_accounts = self._filter_by_media_types(['linkedin'])
        super(SocialAccountLinkedin, (self - linkedin_accounts))._compute_statistics()

        for account in linkedin_accounts:
            all_stats_dict = account._compute_statistics_linkedin()
            month_stats_dict = account._compute_statistics_linkedin(last_30d=True)
            # compute trend
            for stat_name in list(all_stats_dict.keys()):
                all_stats_dict['%s_trend' % stat_name] = self._compute_trend(all_stats_dict.get(stat_name, 0), month_stats_dict.get(stat_name, 0))
            # store statistics
            account.write(all_stats_dict)

    def _linkedin_fetch_followers_count(self):
        """Fetch number of followers from the LinkedIn API."""
        self.ensure_one()
        endpoint = url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'networkSizes/urn:li:organization:%s' % self.linkedin_account_id)
        # removing X-Restli-Protocol-Version header for this endpoint as it is not required according to LinkedIn Doc.
        # using this header with an endpoint that doesn't support it will cause the request to fail
        headers = self._linkedin_bearer_headers()
        headers.pop('X-Restli-Protocol-Version', None)
        response = requests.get(
            endpoint,
            params={'edgeType': 'CompanyFollowedByMember'},
            headers=headers,
            timeout=3)
        if response.status_code != 200:
            return 0
        return response.json().get('firstDegreeSize', 0)

    def _compute_statistics_linkedin(self, last_30d=False):
        """Fetch statistics from the LinkedIn API.

        :param last_30d: If `True`, return the statistics of the last 30 days
                      Else, return the statistics of all the time.

            If we want statistics for the month, we need to choose the granularity
            "month". The time range has to be bigger than the granularity and
            if we have result over 1 month and 1 day (e.g.), the API will return
            2 results (one for the month and one for the day).
            To avoid this, we simply move the end date in the future, so we have
            result  only for this month, in one simple dict.
        """
        self.ensure_one()

        endpoint = url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'organizationalEntityShareStatistics')
        params = {
            'q': 'organizationalEntity',
            'organizationalEntity': self.linkedin_account_urn
        }

        if last_30d:
            # The LinkedIn API take timestamp in milliseconds
            end = int((datetime.now() + timedelta(days=2)).timestamp() * 1000)
            start = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            endpoint += '?timeIntervals=%s' % '(timeRange:(start:%i,end:%i),timeGranularityType:MONTH)' % (start, end)

        response = requests.get(
            endpoint,
            params=params,
            headers=self._linkedin_bearer_headers(),
            timeout=5)

        if response.status_code != 200:
            return {}

        data = response.json().get('elements', [{}])[0].get('totalShareStatistics', {})

        return {
            'audience': self._linkedin_fetch_followers_count(),
            'engagement': data.get('clickCount', 0) + data.get('likeCount', 0) + data.get('commentCount', 0),
            'stories': data.get('shareCount', 0) + data.get('shareMentionsCount', 0),
        }

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SocialAccountLinkedin, self).create(vals_list)

        linkedin_accounts = res.filtered(lambda account: account.media_type == 'linkedin')
        if linkedin_accounts:
            linkedin_accounts._create_default_stream_linkedin()

        return res

    def _linkedin_bearer_headers(self, linkedin_access_token=None):
        if linkedin_access_token is None:
            linkedin_access_token = self.linkedin_access_token
        return {
            'Authorization': 'Bearer %s' % linkedin_access_token,
            'cache-control': 'no-cache',
            'X-Restli-Protocol-Version': '2.0.0'
        }

    def _get_linkedin_accounts(self, linkedin_access_token):
        """Make an API call to get all LinkedIn pages linked to the actual access token."""
        response = requests.get(
            url_join(self.env['social.media']._LINKEDIN_ENDPOINT, 'organizationAcls'),
            params={
                'q': 'roleAssignee',
                'role': 'ADMINISTRATOR',
                'projection': '(elements*(*,organization~(%s)))' % self.env['social.media']._LINKEDIN_ORGANIZATION_PROJECTION,
            },
            headers=self._linkedin_bearer_headers(linkedin_access_token),
            timeout=5).json()

        # Avoid duplicates accounts
        accounts = []
        accounts_urn = []
        if 'elements' in response and isinstance(response.get('elements'), list):
            for organization in response.get('elements'):
                if organization.get('state') != 'APPROVED':
                    continue
                image_url = self._extract_linkedin_picture_url(organization.get('organization~'))
                image_data = requests.get(image_url, timeout=10).content if image_url else None
                account_urn = organization.get('organization')
                if account_urn not in accounts_urn:
                    accounts_urn.append(account_urn)
                    accounts.append({
                        'name': organization.get('organization~', {}).get('localizedName'),
                        'linkedin_account_urn': account_urn,
                        'linkedin_access_token': linkedin_access_token,
                        'social_account_handle': organization.get('organization~', {}).get('vanityName'),
                        'image': base64.b64encode(image_data) if image_data else False,
                    })

        return accounts

    def _create_linkedin_accounts(self, access_token, media):
        linkedin_accounts = self._get_linkedin_accounts(access_token)
        if not linkedin_accounts:
            raise SocialValidationException(_('There is no page linked to this account'))

        social_accounts = self.sudo().with_context(active_test=False).search([
            ('media_id', '=', media.id),
            ('linkedin_account_urn', 'in', [l.get('linkedin_account_urn') for l in linkedin_accounts])])

        error_message = social_accounts._get_multi_company_error_message()
        if error_message:
            raise SocialValidationException(error_message)

        existing_accounts = {
            account.linkedin_account_urn: account
            for account in social_accounts
            if account.linkedin_account_urn
        }

        accounts_to_create = []
        for account in linkedin_accounts:
            if account['linkedin_account_urn'] in existing_accounts:
                existing_accounts[account['linkedin_account_urn']].write({
                    'active': True,
                    'linkedin_access_token': account.get('linkedin_access_token'),
                    'social_account_handle': account.get('username'),
                    'is_media_disconnected': False,
                    'image': account.get('image')
                })
            else:
                account.update({
                    'media_id': media.id,
                    'is_media_disconnected': False,
                    'has_trends': True,
                    'has_account_stats': True,
                })
                accounts_to_create.append(account)

        self.create(accounts_to_create)

    def _create_default_stream_linkedin(self):
        """Create a stream for each organization page."""
        page_posts_stream_type = self.env.ref('social_linkedin.stream_type_linkedin_company_post')

        streams_to_create = [{
            'media_id': account.media_id.id,
            'stream_type_id': page_posts_stream_type.id,
            'account_id': account.id
        } for account in self if account.linkedin_account_urn]

        if streams_to_create:
            self.env['social.stream'].create(streams_to_create)

    def _extract_linkedin_picture_url(self, json_data):
        """The LinkedIn API returns a very complicated and nested structure for author/company information.
        This method acts as a helper to extract the image URL from the passed data."""
        elements = None
        if json_data and 'logoV2' in json_data:
            # company picture
            elements = json_data.get('logoV2', {}).get('original~', {})
        elif json_data and 'profilePicture' in json_data:
            # personal picture
            elements = json_data.get('profilePicture', {}).get('displayImage~', {})
        if elements:
            return elements.get('elements', [{}])[0].get('identifiers', [{}])[0].get('identifier', '')
        return ''
