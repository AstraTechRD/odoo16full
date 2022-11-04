# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from pprint import pformat
from xml.etree import ElementTree

import requests
from werkzeug.urls import url_encode, url_join, url_parse

from odoo import _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.sale_amazon import const


_logger = logging.getLogger(__name__)


#=== CUSTOM EXCEPTION CLASSES ===#

class AmazonRateLimitError(Exception):
    """ When the API rate limit of Amazon is reached. """

    def __init__(self, operation):
        self.operation = operation
        super().__init__()


#=== ONBOARDING ===#

def exchange_authorization_code(authorization_code, account):
    """ Exchange the LWA authorization code for the LWA refresh token and save it on the account.

    :param str authorization_code: The authorization code to exchange with the LWA refresh token.
    :param recordset account: The account for which a refresh token must be exchanged, as an
                              `amazon.account` record.
    :return: None
    """
    data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
    }
    endpoint = const.PROXY_ENDPOINTS['authorization']
    response_content = make_proxy_request(endpoint, account.env, payload=data)
    account.refresh_token = response_content['refresh_token']


def ensure_account_is_set_up(account, require_marketplaces=True):
    """ Ensure that the fields required for SP-API calls are filled.

    This method must be called at the start of every flow that require making API requests. If a
    flow makes several API requests in a row, it is enough to only call this method before the first
    request is made.

    :param recordset account: The account for which the fields must be checked, as an
                              `amazon.account` record.
    :param bool require_marketplaces: Whether the field `active_marketplace_ids` is considered
                                      required or not.
    :return: None
    :raise UserError: If one of the required fields is not filled.
    """
    # Check that the API keys and tokens are set.
    if not account.refresh_token or not account.seller_key:
        raise UserError(_("You first need to authorize the Amazon account %s.") % account.name)
    # Check that the marketplaces are set when required.
    if require_marketplaces and not account.active_marketplace_ids:
        raise UserError(_(
            "You first need to set the marketplaces to synchronize for the Amazon account %s."
        ) % account.name)


#=== PROXY COMMUNICATIONS ===#

def make_proxy_request(endpoint, env, payload=None):
    """ Make a request to the Amazon proxy at the specified endpoint.

    :param str endpoint: The proxy endpoint to be reached by the request.
    :param Environment env: An `odoo.api.Environment`.
    :param dict payload: The Amazon-specific payload of the request.
    :return: The JSON-formatted content of the response.
    :rtype: dict
    :raise ValidationError: If a `RequestException` occurs.
    """
    url = url_join(const.PROXY_URL, endpoint)
    ICP = env['ir.config_parameter']
    data = {
        'db_uuid': ICP.sudo().get_param('database.uuid'),
        'db_enterprise_code': ICP.sudo().get_param('database.enterprise_code'),
        'amazon_data': json.dumps(payload or {}),
    }
    try:
        response = requests.post(url, data=data, timeout=60)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            response_content = response.json()
            error_code = response_content.get('error')
            error_description = response_content.get('error_description')
            _logger.exception(
                "Invalid API request (error code: %s, description: %s) with data:\n%s",
                error_code, error_description, pformat(data)
            )
            raise ValidationError(
                _("Error code: %s; description: %s") % (error_code, error_description)
            )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.exception("Could not establish the connection to the proxy.")
        raise ValidationError(_("Could not establish the connection to the proxy."))
    return response.json()


#=== API COMMUNICATIONS ===#

def make_sp_api_request(account, operation, path_parameter='', payload=None, method='GET'):
    """ Make a request to the SP-API for the specified operation.

    See https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api.

    Note: account.ensure_one()

    :param recordset account: The Amazon account on behalf of which the request is made.
    :param str operation: The SP-API operation to be called by the request.
    :param str path_parameter: The variable that SP-API paths are interpolated with.
    :param dict payload: The payload of the request.
    :param string method: The HTTP method of the request ('GET' or 'POST').
    :return: The JSON-formatted content of the response.
    :rtype: dict
    :raise ValidationError: If an HTTP error occurs.
    :raise AmazonRateLimitError: If the rate limit was reached.
    """
    account.ensure_one()

    # Build the request URL based on the API path and domain.
    path = const.API_OPERATIONS_MAPPING[operation]['url_path'].format(param=path_parameter)
    domain = const.API_DOMAINS_MAPPING[account.base_marketplace_id.region]
    url = url_join(domain, path)

    payload = payload or {}

    # Refresh the credentials used to sign the request.
    if const.API_OPERATIONS_MAPPING[operation]['restricted_resource_path'] is None:  # No RDT is required
        refresh_access_token(account)
        access_token = account.access_token
    else:  # The operation requires an RDT to access restricted data.
        refresh_restricted_data_token(account)
        access_token = account.restricted_data_token
    refresh_aws_credentials(account)

    # Build the request headers
    host = url_parse(domain).netloc
    now = datetime.utcnow()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
        'host': host,
        'x-amz-access-token': access_token,
        'x-amz-security-token': account.aws_session_token,
        'x-amz-date': now.strftime('%Y%m%dT%H%M%SZ'),
        'Authorization': compute_authorization_header(account, host, path, method, payload, now),
    }
    try:
        if method == 'GET':
            response = requests.get(url, params=payload, headers=headers, timeout=60)
        else:  # 'POST'
            response = requests.post(url, json=payload, headers=headers, timeout=60)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            if response.status_code == 429:
                raise AmazonRateLimitError(operation)
            else:
                errors = response.json().get('errors')
                error_code = errors and errors[0].get('code')
                error_message = errors and errors[0].get('message')
                _logger.exception(
                    "Invalid API request (error code: %s, description: %s) with data:\n%s",
                    error_code, error_message, pformat(payload)
                )
                raise ValidationError(_(
                    "The communication with the API failed.\nError code: %s; description: %s"
                ) % (error_code, error_message))
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.exception("Unable to reach endpoint at %s", url)
        raise ValidationError(_("Could not establish the connection to the API."))
    return response.json()


def refresh_access_token(account):
    """ Request a new LWA access token if it is expired and save it on the account.

    :param recordset account: The account for which an access token must be requested, as an
                              `amazon.account` record.
    :return: None
    """
    if datetime.utcnow() > account.access_token_expiry - timedelta(minutes=5):
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': account.refresh_token,
        }
        endpoint = const.PROXY_ENDPOINTS['authorization']
        response_content = make_proxy_request(endpoint, account.env, payload=payload)
        account.write({
            'access_token': response_content['access_token'],
            'access_token_expiry': datetime.utcnow() + timedelta(
                seconds=response_content['expires_in']
            ),
        })


def refresh_restricted_data_token(account):
    """ Request a new Restricted Data Token (RDT) if it is expired and save it on the account.

    The request includes the restricted path of all restricted operation to avoid refreshing the RDT
    for each new operation.

    :param recordset account: The account for which a Restricted Data Token must be requested, as an
                              `amazon.account` record.
    :return: None
    """
    if datetime.utcnow() > account.restricted_data_token_expiry - timedelta(minutes=5):
        all_restricted_operations = [
            k for k, map in const.API_OPERATIONS_MAPPING.items() if map['restricted_resource_path']
        ]
        OPERATIONS_MAPPING = const.API_OPERATIONS_MAPPING
        payload = {
            'restrictedResources': [{
                'method': 'GET',
                'path': OPERATIONS_MAPPING[operation]['restricted_resource_path'],
                'dataElements': OPERATIONS_MAPPING[operation]['restricted_resource_data_elements'],
            } for operation in all_restricted_operations]
        }
        response_content = make_sp_api_request(
            account, 'createRestrictedDataToken', payload=payload, method='POST'
        )
        account.write({
            'restricted_data_token': response_content['restrictedDataToken'],
            'restricted_data_token_expiry': datetime.utcnow() + timedelta(
                seconds=response_content['expiresIn']
            ),
        })


def refresh_aws_credentials(accounts):
    """ Request new AWS credentials if they are expired and save them on the accounts.

    If multiple accounts are provided, the AWS credentials of the first account are refreshed and
    copied to the other accounts. Since the credentials are the same for all accounts, we can thus
    avoid making redundant requests.

    :param recordset accounts: The accounts for which the AWS credentials must be requested, as an
                               `amazon.account` recordset.
    :return: None
    """
    if not accounts:
        return

    aws_credentials_expiry = accounts[0].aws_credentials_expiry
    if datetime.utcnow() > aws_credentials_expiry - timedelta(minutes=5):
        endpoint = const.PROXY_ENDPOINTS['aws_tokens']
        payload = {
            'Action': 'AssumeRole',
            'Version': '2011-06-15',
        }
        response_content = make_proxy_request(endpoint, accounts.env, payload=payload)
        aws_credentials = response_content['AssumeRoleResponse']['AssumeRoleResult']['Credentials']
        accounts.write({
            'aws_access_key': aws_credentials['AccessKeyId'],
            'aws_secret_key': aws_credentials['SecretAccessKey'],
            'aws_session_token': aws_credentials['SessionToken'],
            'aws_credentials_expiry': datetime.utcnow() + timedelta(hours=1),
        })


def compute_authorization_header(account, host, path, method, payload, request_datetime):
    """ Compute the authorization header of an SP-API request.

    :param recordset account: The Amazon account on behalf of which the request is made, as an
                              `amazon.account` record.
    :param string host: The domain of the request.
    :param string path: The URL path of the request.
    :param string method: The HTTP method of the request.
    :param dict payload: The payload of the request.
    :param datetime request_datetime: The datetime of the request.
    :return: The authorization header of the request. For example, a typical return value could be:
             'AWS4-HMAC-SHA256 ' \
             'Credential=AKIAY7OS2NMOYQMG6/20210621/us-east-1/execute-api/aws4_request, ' \
             'SignedHeaders=host;x-amz-date;x-amz-security-token, ' \
             'Signature=e37bcfd80a7baefea5968e0c6344083c8c429af76e924f7eff050c193843'
    :rtype: str
    """
    # 0. Set the scope variables.
    formatted_request_date = request_datetime.strftime('%Y%m%d')
    formatted_request_datetime = request_datetime.strftime('%Y%m%dT%H%M%SZ')
    region = account.base_marketplace_id.region
    service = 'execute-api'
    credential_scope = '/'.join([formatted_request_date, region, service, 'aws4_request'])

    # 1. Create a Canonical_request
    if method == 'GET':
        canonical_query_string = url_encode((k, payload[k]) for k in sorted(payload.keys()))
    else:
        canonical_query_string = ''  # `body_string` is populated instead.
    canonical_headers = f'host:{host}\n' \
                        f'x-amz-date:{formatted_request_datetime}\n' \
                        f'x-amz-security-token:{account.aws_session_token}\n'
    signed_headers = 'host;x-amz-date;x-amz-security-token'
    body_string = '' if method == 'GET' else json.dumps(payload)
    payload_hash = hashlib.sha256(body_string.encode()).hexdigest()
    canonical_request = '\n'.join([
        method,
        path or '/',
        canonical_query_string,         # sorted parameters with key-value
        canonical_headers,              # sorted headers signed with key-value
        signed_headers,                 # sorted headers with only key
        payload_hash                    # hashed parameters
    ])
    canonical_request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()

    # 2. Create a string to sign.
    algorithm = 'AWS4-HMAC-SHA256'
    signing_string = '\n'.join(
        [algorithm, formatted_request_datetime, credential_scope, canonical_request_hash]
    )

    # 3. Calculate the signature.
    k_date = hmac.new(
        ('AWS4' + account.aws_secret_key).encode(), formatted_request_date.encode(), hashlib.sha256
    ).digest()
    k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, 'aws4_request'.encode(), hashlib.sha256).digest()
    signature = hmac.new(k_signing, signing_string.encode(), hashlib.sha256).hexdigest()

    # 4. Add the signing information.
    authorization_header = f'{algorithm} ' \
                           f'Credential={account.aws_access_key}/{credential_scope}, ' \
                           f'SignedHeaders={signed_headers}, ' \
                           f'Signature={signature}'
    return authorization_header


#=== FEEDS MANAGEMENT ===#

def build_feed(account, message_type, messages_builder, *args, **kwargs):
    """ Build XML feed data to be sent to the SP-API.

    :param recordset account: The Amazon account on behalf of which the feed should be built, as an
                              `amazon.account` record.
    :param str message_type: The category of the feed to be built.
    :param function messages_builder: The function to build the 'Message' elements.
    :param list args: The arguments to pass to the `messages_builder` function.
    :param dict kwargs: The keyword arguments to pass to the `messages_builder` function.
    :return: The XML feed.
    :rtype: str
    """
    XSI = 'http://www.w3.org/2001/XMLSchema-instance'
    root = ElementTree.Element(
        'AmazonEnvelope', {f'{"{" + XSI + "}"}noNamespaceSchemaLocation': 'amzn-envelope.xsd'}
    )
    header = ElementTree.SubElement(root, 'Header')
    ElementTree.SubElement(header, 'DocumentVersion').text = '1.01'
    ElementTree.SubElement(header, 'MerchantIdentifier').text = account.seller_key
    ElementTree.SubElement(root, 'MessageType').text = message_type
    messages_builder(root, *args, **kwargs)
    for i, message in enumerate(root.findall('Message')):
        message_id = ElementTree.Element('MessageID')
        message_id.text = f'{int(datetime.utcnow().timestamp())}{i}'
        message.insert(0, message_id)  # Insert the message ID before the other elements.
    return ElementTree.tostring(root, encoding='UTF-8', method='xml')


def submit_feed(account, feed, feed_type):
    """ Submit the provided feed to the SP-API.

    :param recordset account: The Amazon account on behalf of which the feed should be submitted, as
                              an `amazon.account` record.
    :param str feed: The XML feed to submit.
    :param str feed_type: The type of the feed to submit. E.g., 'POST_ORDER_ACKNOWLEDGEMENT_DATA'.
    :return: The feed id returned by the SP-API.
    :rtype: str
    """
    def _create_feed_document():
        """ Create a feed document.

        :return: The feed document id and the pre-signed URL to upload the feed to.
        :rtype: tuple[str, str]
        """
        _payload = {'contentType': feed_content_type}
        _response_content = make_sp_api_request(
            account, 'createFeedDocument', payload=_payload, method='POST'
        )
        return _response_content['feedDocumentId'], _response_content['url']

    def _upload_feed_data():
        """ Upload the XML feed to the URL returned by Amazon.

        :return: None
        """
        headers = {'content-Type': feed_content_type}
        try:
            response = requests.put(upload_url, data=feed, headers=headers, timeout=60)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception("Invalid API request with data:\n%s", feed)
                raise ValidationError(_("The communication with the API failed."))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Could not establish the connection to the feed URL.")
            raise ValidationError(_("Could not establish the connection to the feed URL."))

    def _create_feed():
        """ Create the feed and return its id.

        :return: The feed id.
        :rtype: str
        """
        _marketplace_api_refs = account.active_marketplace_ids.mapped('api_ref')
        _payload = {
            'feedType': feed_type,
            'marketplaceIds': _marketplace_api_refs,
            'inputFeedDocumentId': feed_document_id,
        }
        _response_content = make_sp_api_request(
            account, 'createFeed', payload=_payload, method='POST'
        )
        return _response_content['feedId']

    feed_content_type = 'text/xml; charset=UTF-8'
    feed_document_id, upload_url = _create_feed_document()
    _upload_feed_data()
    feed_id = _create_feed()
    return feed_id


#=== HELPERS ====#

def pull_batch_data(account, operation, payload, path_parameter='', method='GET'):
    """ Pull a batch of data from the SP-API.

    If request results are paginated, the 'NextToken' returned with the response is added to the
    payload to pull the next page's batch with the following call.

    :param recordset account: The Amazon account on behalf of which the data must be pulled.
    :param str operation: The SP-API operation to be called by the request.
    :param dict payload: The payload of the request.
    :param str path_parameter: The variable that SP-API paths are interpolated with.
    :param string method: The HTTP method of the request ('GET' or 'POST').
    :return: The batch data and whether a next page exists.
    :rtype: tuple[dict, bool]
    """
    response_content = make_sp_api_request(
        account, operation, path_parameter=path_parameter, payload=payload, method=method
    )
    batch_data = response_content['payload']
    next_token = response_content['payload'].get('NextToken')
    has_next_page = bool(next_token)
    payload['NextToken'] = next_token
    return batch_data, has_next_page


@contextmanager
def preserve_credentials(account):
    """ Context manager to load credentials from the account and save them again when exiting.

    Use this in situations where the cache is invalidated and you need to re-use the credentials.

    :param recordset account: The Amazon account whose credentials must be preserved, as a
                              `amazon.account` record.
    :return: None
    """
    fields_to_preserve = [
        'access_token',
        'access_token_expiry',
        'aws_access_key',
        'aws_secret_key',
        'aws_session_token',
        'aws_credentials_expiry',
        'restricted_data_token',
        'restricted_data_token_expiry',
    ]
    credentials = {field: account[field] for field in fields_to_preserve}  # Load credentials.
    yield  # Execute the code in the context.
    account.write(credentials)  # Restore credentials.
