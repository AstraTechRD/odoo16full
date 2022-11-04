# -*- coding: utf-8 -*-

import requests
import logging
import re
import odoo
import odoo.release
from dateutil.relativedelta import relativedelta

from requests.exceptions import RequestException, Timeout, ConnectionError
from odoo import api, fields, models, _
from odoo.tools import format_date
from odoo.exceptions import UserError, CacheMiss, MissingError, ValidationError
from odoo.addons.account_online_synchronization.models.odoofin_auth import OdooFinAuth
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)
pattern = re.compile("^[a-z0-9-_]+$")

class AccountOnlineAccount(models.Model):
    _name = 'account.online.account'
    _description = 'representation of an online bank account'

    name = fields.Char(string="Account Name", help="Account Name as provided by third party provider")
    online_identifier = fields.Char(help='Id used to identify account by third party provider', readonly=True)
    balance = fields.Float(readonly=True, help='Balance of the account sent by the third party provider')
    account_number = fields.Char(help='Set if third party provider has the full account number')
    account_data = fields.Char(help='Extra information needed by third party provider', readonly=True)

    account_online_link_id = fields.Many2one('account.online.link', readonly=True, ondelete='cascade')
    journal_ids = fields.One2many('account.journal', 'account_online_account_id', string='Journal', domain=[('type', '=', 'bank')])
    last_sync = fields.Date("Last synchronization")
    company_id = fields.Many2one('res.company', related='account_online_link_id.company_id')
    currency_id = fields.Many2one('res.currency')

    inverse_balance_sign = fields.Boolean(
        string="Inverse Balance Sign",
        help="If checked, the balance sign will be inverted",
    )
    inverse_transaction_sign = fields.Boolean(
        string="Inverse Transaction Sign",
        help="If checked, the transaction sign will be inverted",
    )

    @api.constrains('journal_ids')
    def _check_journal_ids(self):
        if len(self.journal_ids) > 1:
            raise ValidationError(_('You cannot have two journals associated with the same Online Account.'))

    def unlink(self):
        online_link = self.mapped('account_online_link_id')
        res = super(AccountOnlineAccount, self).unlink()
        for link in online_link:
            if len(link.account_online_account_ids) == 0:
                link.unlink()
        return res

    def _refresh(self):
        data = {'account_id': self.online_identifier}
        while True:
            # While this is kind of a bad practice to do, it can happen that provider_data/account_data change between
            # 2 calls, the reason is that those field contains the encrypted information needed to access the provider
            # and first call can result in an error due to the encrypted token inside provider_data being expired for example.
            # In such a case, we renew the token with the provider and send back the newly encrypted token inside provider_data
            # which result in the information having changed, henceforth why those fields are passed at every loop.
            data.update({
                'provider_data': self.account_online_link_id.provider_data,
                'account_data': self.account_data
            })
            resp_json = self.account_online_link_id._fetch_odoo_fin('/proxy/v1/refresh', data=data)
            if resp_json.get('account_data'):
                self.account_data = resp_json['account_data']
            if resp_json.get('code') == 300:
                return resp_json.get('data', {}).get('mode', 'error')
            if not resp_json.get('next_data'):
                break
            data['next_data'] = resp_json.get('next_data') or {}
        return True

    def _retrieve_transactions(self):
        start_date = self.last_sync or fields.Date().today() - relativedelta(days=15)
        last_stmt_line = self.env['account.bank.statement.line'].search([
                ('date', '<=', start_date),
                ('online_transaction_identifier', '!=', False),
                ('journal_id', 'in', self.journal_ids.ids),
                ('online_account_id', '=', self.id)
            ], order="date desc", limit=1)
        transactions = []
        data = {
            'start_date': format_date(self.env, start_date, date_format='yyyy-MM-dd'),
            'account_id': self.online_identifier,
            'last_transaction_identifier': last_stmt_line.online_transaction_identifier,
            'currency_code': self.journal_ids[0].currency_id.name,
        }
        while True:
            # While this is kind of a bad practice to do, it can happen that provider_data/account_data change between
            # 2 calls, the reason is that those field contains the encrypted information needed to access the provider
            # and first call can result in an error due to the encrypted token inside provider_data being expired for example.
            # In such a case, we renew the token with the provider and send back the newly encrypted token inside provider_data
            # which result in the information having changed, henceforth why those fields are passed at every loop.
            data.update({
                'provider_data': self.account_online_link_id.provider_data,
                'account_data': self.account_data
            })
            resp_json = self.account_online_link_id._fetch_odoo_fin('/proxy/v1/transactions', data=data)
            if resp_json.get('balance'):
                sign = -1 if self.inverse_balance_sign else 1
                self.balance = sign * resp_json['balance']
            if resp_json.get('account_data'):
                self.account_data = resp_json['account_data']
            transactions += resp_json.get('transactions', [])
            if not resp_json.get('next_data'):
                break
            data['next_data'] = resp_json.get('next_data') or {}

        return self.env['account.bank.statement.line']._online_sync_bank_statement(transactions, self)


class AccountOnlineLink(models.Model):
    _name = 'account.online.link'
    _description = 'Bank Connection'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _compute_next_synchronization(self):
        for rec in self:
            rec.next_refresh = self.env['ir.cron'].sudo().search([('id', '=', self.env.ref('account_online_synchronization.online_sync_cron').id)], limit=1).nextcall

    account_online_account_ids = fields.One2many('account.online.account', 'account_online_link_id')
    last_refresh = fields.Datetime(readonly=True, default=fields.Datetime.now())
    next_refresh = fields.Datetime("Next synchronization", compute='_compute_next_synchronization')
    state = fields.Selection([('connected', 'Connected'), ('error', 'Error'), ('disconnected', 'Not Connected')],
                             default='disconnected', tracking=True, required=True, readonly=True)
    auto_sync = fields.Boolean(default=True, string="Automatic synchronization",
                               help="If possible, we will try to automatically fetch new transactions for this record")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    # Information received from OdooFin, should not be tampered with
    name = fields.Char(help="Institution Name", readonly=True)
    client_id = fields.Char(help="Represent a link for a given user towards a banking institution", readonly=True)
    refresh_token = fields.Char(help="Token used to sign API request, Never disclose it",
                                readonly=True, groups="base.group_system")
    access_token = fields.Char(help="Token used to access API.", readonly=True, groups="account.group_account_user")
    provider_data = fields.Char(help="Information needed to interact with third party provider", readonly=True)
    expiring_synchronization_date = fields.Date(help="Date when the consent for this connection expires",
                                                readonly=True)

    ##########################
    # Wizard opening actions #
    ##########################

    @api.model
    def create_new_bank_account_action(self):
        view_id = self.env.ref('account.setup_bank_account_wizard').id
        ctx = self.env.context
        # if this was called from kanban box, active_model is in context
        if self.env.context.get('active_model') == 'account.journal':
            ctx = {**ctx, 'default_linked_journal_id': ctx.get('journal_id', False)}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create a Bank Account'),
            'res_model': 'account.setup.bank.manual.config',
            'target': 'new',
            'view_mode': 'form',
            'context': ctx,
            'views': [[view_id, 'form']]
        }

    def _link_accounts_to_journals_action(self, accounts):
        """
        This method opens a wizard allowing the user to link
        his bank accounts with new or existing journal.
        :return: An action openning a wizard to link bank accounts with account journal.
        """
        self.ensure_one()
        account_link_journal_wizard = self.env['account.link.journal'].create({
            'number_added': len(accounts),
            'account_ids': [(0, 0, {
                'online_account_id': online_account.id,
                'journal_id': online_account.journal_ids[0].id if online_account.journal_ids else None
            }) for online_account in accounts]
        })

        return {
            "name": _("Link Account to Journal"),
            "type": "ir.actions.act_window",
            "res_model": "account.link.journal",
            "views": [[False, "form"]],
            "target": "new",
            "res_id": account_link_journal_wizard.id
        }

    def _show_fetched_transactions_action(self, stmt_line_ids):
        if self.env.context.get('dont_show_transactions'):
            return
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[('id', 'in', stmt_line_ids.ids)],
            name=_('Fetched Transactions'),
        )

    #######################################################
    # Generic methods to contact server and handle errors #
    #######################################################

    def _fetch_odoo_fin(self, url, data=None, ignore_status=False):
        """
        Method used to fetch data from the Odoo Fin proxy.
        :param url: Proxy's URL end point.
        :param data: HTTP data request.
        :return: A dict containing all data.
        """
        if not data:
            data = {}
        if self.state == 'disconnected' and not ignore_status:
            raise UserError(_('Please reconnect your online account.'))

        timeout = int(self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.request_timeout')) or 60
        proxy_mode = self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.proxy_mode') or 'production'
        if not pattern.match(proxy_mode):
            raise UserError(_('Invalid value for proxy_mode config parameter.'))
        endpoint_url = 'https://%s.odoofin.com%s' % (proxy_mode, url)
        data['utils'] = {
            'request_timeout': timeout,
            'lang': get_lang(self.env).code,
            'server_version': odoo.release.serie,
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'cron': self.env.context.get('cron', False)
        }

        try:
            # We have to use sudo to pass record as some fields are protected from read for common users.
            resp = requests.post(url=endpoint_url, json=data, timeout=timeout, auth=OdooFinAuth(record=self.sudo()))
            resp_json = resp.json()
            return self._handle_response(resp_json, url, data, ignore_status)
        except (Timeout, ConnectionError, RequestException, ValueError):
            _logger.exception('synchronization error')
            raise UserError(
                _("The online synchronization service is not available at the moment. "
                  "Please try again later."))

    def _handle_response(self, resp_json, url, data, ignore_status=False):
        # Response is a json-rpc response, therefore data is encapsulated inside error in case of error
        # and inside result in case of success.
        if not resp_json.get('error'):
            result = resp_json.get('result')
            state = result.get('odoofin_state') or False
            message = result.get('display_message') or False
            subject = message and _('Message') or False
            self._log_information(state=state, message=message, subject=subject)
            if result.get('provider_data'):
                # Provider_data is extremely important and must be saved as soon as we received it
                # as it contains encrypted credentials from external provider and if we loose them we
                # loose access to the bank account, As it is possible that provider_data
                # are received during a transaction containing multiple calls to the proxy, we ensure
                # that provider_data is commited in database as soon as we received it.
                self.provider_data = result.get('provider_data')
                self.env.cr.commit()
            return result
        else:
            error = resp_json.get('error')
            # Not considered as error
            if error.get('code') == 101: # access token expired, not an error
                self._get_access_token()
                return self._fetch_odoo_fin(url, data, ignore_status)
            elif error.get('code') == 102: # refresh token expired, not an error
                self._get_refresh_token()
                self._get_access_token()
                # We need to commit here because if we got a new refresh token, and a new access token
                # It means that the token is active on the proxy and any further call resulting in an
                # error would lose the new refresh_token hence blocking the account ad vitam eternam
                self.env.cr.commit()
                return self._fetch_odoo_fin(url, data, ignore_status)
            elif error.get('code') == 300: # redirect, not an error
                return error
            # If we are in the process of deleting the record ignore code 100 (invalid signature), 104 (account deleted)
            # 106 (provider_data corrupted) and allow user to delete his record from this side.
            elif error.get('code') in (100, 104, 106) and self.env.context.get('delete_sync'):
                return {'delete': True}
            # Log and raise error
            error_details = error.get('data')
            subject = error.get('message')
            message = error_details.get('message')
            if error_details.get('error_reference'):
                message += '\n' + _('The reference of your error is %s. Please mention it when contacting Odoo support.') % error_details['error_reference']
            state = error_details.get('odoofin_state') or 'error'

            self._log_information(state=state, subject=subject, message=message, reset_tx=True)

    def _log_information(self, state, subject=None, message=None, reset_tx=False):
        # If the reset_tx flag is passed, it means that we have an error, and we want to log it on the record
        # and then raise the error to the end user. To do that we first roll back the current transaction,
        # then we write the error on the record, we commit those changes, and finally we raise the error.
        if reset_tx:
            self.env.cr.rollback()
        try:
            # if state is disconnected, and newstate is error: ignore it
            if state == 'error' and self.state == 'disconnected':
                state = 'disconnected'
            if subject and message:
                self.message_post(body='<b>%s</b> <br> %s' % (subject, message.replace('\n', '<br>')), subject=subject)
            if state and self.state != state:
                self.write({'state': state})
            if reset_tx:
                # In case of reset_tx, we commit the changes and then raise the error (see comment at the start of the method)
                self.env.cr.commit()
                raise UserError(message)
        except (CacheMiss, MissingError):
            # This exception can happen if record was created and rollbacked due to error in same transaction
            # Therefore it is not possible to log information on it, in this case we just ignore it.
            pass

    ###############
    # API methods #
    ###############

    def _get_access_token(self):
        for link in self:
            resp_json = link._fetch_odoo_fin('/proxy/v1/get_access_token', ignore_status=True)
            link.access_token = resp_json.get('access_token', False)

    def _get_refresh_token(self):
        # Use sudo as refresh_token field is not accessible to most user
        for link in self.sudo():
            resp_json = link._fetch_odoo_fin('/proxy/v1/renew_token', ignore_status=True)
            link.refresh_token = resp_json.get('refresh_token', False)

    def unlink(self):
        to_unlink = self.env['account.online.link']
        for link in self:
            try:
                resp_json = link.with_context(delete_sync=True)._fetch_odoo_fin('/proxy/v1/delete_user', data={'provider_data': link.provider_data}, ignore_status=True) # delete proxy user
                if resp_json.get('delete', True) is True:
                    to_unlink += link
            except UserError as e:
                continue
        if to_unlink:
            return super(AccountOnlineLink, to_unlink).unlink()

    def _fetch_accounts(self, add_new_accounts=True):
        self.ensure_one()
        accounts = {}
        data = {}
        while True:
            # While this is kind of a bad practice to do, it can happen that provider_data changes between
            # 2 calls, the reason is that that field contains the encrypted information needed to access the provider
            # and first call can result in an error due to the encrypted token inside provider_data being expired for example.
            # In such a case, we renew the token with the provider and send back the newly encrypted token inside provider_data
            # which result in the information having changed, henceforth why that field is passed at every loop.
            data['provider_data'] = self.provider_data
            data['add_new_accounts'] = add_new_accounts
            resp_json = self._fetch_odoo_fin('/proxy/v1/accounts', data)
            for acc in resp_json.get('accounts', []):
                acc['account_online_link_id'] = self.id
                currency_id = self.env['res.currency'].with_context(active_test=False).search([('name', '=', acc.pop('currency_code', ''))], limit=1)
                if currency_id:
                    if not currency_id.active:
                        currency_id.active = True
                    acc['currency_id'] = currency_id.id
                accounts[str(acc.get('online_identifier'))] = acc
            if not resp_json.get('next_data'):
                break
            data['next_data'] = resp_json.get('next_data')

        accounts_to_delete = self.env['account.online.account']
        for account in self.account_online_account_ids:
            # pop from accounts to create as it already exists, otherwise mark for deletion
            existing_account = accounts.pop(account.online_identifier, False)
            if existing_account:
                account.account_data = existing_account.get('account_data')
            else:
                accounts_to_delete += account

        accounts_to_delete.unlink()
        new_accounts = self.env['account.online.account']
        if add_new_accounts and accounts:
            new_accounts = self.env['account.online.account'].create(accounts.values())
        return new_accounts

    def _fetch_transactions(self, refresh=True, accounts=False):
        self.ensure_one()
        self.last_refresh = fields.Datetime.now()
        bank_statement_line_ids = self.env['account.bank.statement.line']
        acc = accounts or self.account_online_account_ids
        for online_account in acc:
            # Only get transactions on account linked to a journal
            if online_account.journal_ids:
                if refresh:
                    status = online_account._refresh()
                    if status is not True:
                        return self._open_iframe(status)
                bank_statement_line_ids += online_account._retrieve_transactions()

        return self._show_fetched_transactions_action(bank_statement_line_ids)

    def _get_consent_expiring_date(self):
        self.ensure_one()
        resp_json = self._fetch_odoo_fin('/proxy/v1/consent_expiring_date', ignore_status=True)

        if resp_json.get('consent_expiring_date'):
            expiring_synchronization_date = fields.Date.to_date(resp_json['consent_expiring_date'])
            if expiring_synchronization_date != self.expiring_synchronization_date:
                bank_sync_activity_type_id = self.env.ref('account_online_synchronization.bank_sync_activity_update_consent')
                account_online_link_model_id = self.env['ir.model']._get_id('account.online.link')

                # Remove old activities
                self.env['mail.activity'].search([
                    ('res_id', '=', self.id),
                    ('res_model_id', '=', account_online_link_model_id),
                    ('activity_type_id', '=', bank_sync_activity_type_id.id),
                    ('date_deadline', '<=', self.expiring_synchronization_date),
                    ('user_id', '=', self.env.user.id),
                ]).unlink()

                # Create a new activity
                self.expiring_synchronization_date = expiring_synchronization_date
                self.env['mail.activity'].create({
                    'res_id': self.id,
                    'res_model_id': account_online_link_model_id,
                    'date_deadline': self.expiring_synchronization_date,
                    'summary': _("Bank Synchronization: Update your consent"),
                    'note': resp_json.get('activity_message') or '',
                    'activity_type_id': bank_sync_activity_type_id.id,
                })

    ################################
    # Callback methods from iframe #
    ################################

    def success(self, mode, data):
        if data:
            self.write(data)
            # Provider_data is extremely important and must be saved as soon as we received it
            # as it contains encrypted credentials from external provider and if we loose them we
            # loose access to the bank account, As it is possible that provider_data
            # are received during a transaction containing multiple calls to the proxy, we ensure
            # that provider_data is commited in database as soon as we received it.
            if data.get('provider_data'):
                self.env.cr.commit()

            self._get_consent_expiring_date()
        # if for some reason we just have to update the record without doing anything else, the mode will be set to 'none'
        if mode == 'none':
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        try:
            method_name = '_success_%s' % mode
            method = getattr(self, method_name)
        except AttributeError:
            message = _("This version of Odoo appears to be outdated and does not support the '%s' sync mode. "
                        "Installing the latest update might solve this.", mode)
            _logger.info('Online sync: %s' % (message,))
            self.env.cr.rollback()
            self._log_information(state='error', subject=_('Internal Error'), message=message, reset_tx=True)
            raise UserError(message)
        return method()

    def exchange_token(self, exchange_token):
        self.ensure_one()
        # Exchange token to retrieve client_id and refresh_token from proxy account
        data = {
            'exchange_token': exchange_token,
            'company_id': self.env.company.id,
            'user_id': self.env.user.id
        }
        resp_json = self._fetch_odoo_fin('/proxy/v1/exchange_token', data=data, ignore_status=True)
        # Write in sudo mode as those fields are protected from users
        self.sudo().write({
            'client_id': resp_json.get('client_id'),
            'refresh_token': resp_json.get('refresh_token'),
            'access_token': resp_json.get('access_token')
        })
        return True

    def _success_link(self):
        self.ensure_one()
        self._log_information(state='connected')
        new_accounts = self._fetch_accounts()
        return self._link_accounts_to_journals_action(new_accounts)

    def _success_updateAccounts(self):
        self.ensure_one()
        new_accounts = self._fetch_accounts()
        return self._link_accounts_to_journals_action(new_accounts)

    def _success_updateCredentials(self):
        self.ensure_one()
        self._fetch_accounts(add_new_accounts=False)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _success_refreshAccounts(self):
        self.ensure_one()
        return self._fetch_transactions(refresh=False)

    def _success_reconnect(self):
        self.ensure_one()
        self._log_information(state='connected')
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    ##################
    # action buttons #
    ##################

    def action_new_synchronization(self):
        # Search for an existing link that was not fully connected
        online_link = self
        if not online_link:
            online_link = self.search([('account_online_account_ids', '=', False), ('provider_data', '=', False)], limit=1)
        # If not found, create a new one
        if not online_link:
            online_link = self.create({})
        return online_link._open_iframe('link')

    def action_update_credentials(self):
        return self._open_iframe('updateCredentials')

    def action_initialize_update_accounts(self):
        return self._open_iframe('updateAccounts')

    def action_fetch_transactions(self):
        return self._fetch_transactions()

    def action_reconnect_account(self):
        return self._open_iframe('reconnect')

    def _open_iframe(self, mode='link'):
        self.ensure_one()
        if self.client_id and self.sudo().refresh_token:
            self._get_access_token()
        proxy_mode = self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.proxy_mode') or 'production'
        country = self.env.company.country_id
        action = {
            'type': 'ir.actions.client',
            'tag': 'odoo_fin_connector',
            'id': self.id,
            'params': {
                'proxyMode': proxy_mode,
                'clientId': self.client_id,
                'accessToken': self.access_token,
                'mode': mode,
                'includeParam': {
                    'lang': get_lang(self.env).code,
                    'countryCode': country.code,
                    'countryName': country.display_name,
                    'serverVersion': odoo.release.serie
                }
            }
        }
        if self.provider_data:
            action['params']['providerData'] = self.provider_data

        if mode == 'link':
            user_partner_id = self.env.user.partner_id
            action['params']['includeParam']['phoneNumber'] = user_partner_id.mobile or user_partner_id.phone or ''
            action['params']['includeParam']['dbUuid'] = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return action
