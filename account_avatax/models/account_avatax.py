# -*- coding: utf-8 -*-

from pprint import pformat
from datetime import datetime
import logging

from odoo.addons.account_avatax.lib.avatax_client import AvataxClient
from odoo import models, fields, api, registry, _, SUPERUSER_ID
from odoo.release import version
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round, float_repr

logger = logging.getLogger(__name__)


class AccountAvatax(models.AbstractModel):
    """Enable communication with Avatax for various business documents.

    The business documents should implement
      * _get_avatax_invoice_lines
      * _get_avatax_dates
      * _get_avatax_document_type
    It can then use
      * _map_avatax to tell which taxes should be applied on which document
      * _uncommit_avatax_transaction (optional) to uncommit a transaction in avatax
    """

    _name = 'account.avatax'
    _inherit = ['account.avatax.unique.code']
    _description = 'Mixin to manage taxes with Avatax on various business documents'

    # Technical field used for the visibility of fields and buttons
    is_avatax = fields.Boolean(compute='_compute_is_avatax')

    @api.constrains('partner_id', 'fiscal_position_id')
    def _check_address(self):
        for record in self.filtered('fiscal_position_id.is_avatax'):
            partner = record.partner_id
            country = partner.country_id
            if not country or (country.zip_required and not partner.zip) or (country.state_required and not partner.state_id):
                raise ValidationError(_('Customers are required to have a zip, state and country when using Avatax.'))

    @api.depends('company_id', 'fiscal_position_id')
    def _compute_is_avatax(self):
        for record in self:
            record.is_avatax = record.fiscal_position_id.is_avatax

    # #############################################################################################
    # TO IMPLEMENT IN BUSINESS DOCUMENT
    # #############################################################################################

    def _get_avatax_invoice_lines(self):
        """Get the lines items to send to Avatax.

        :return (list<dict>): the values of the lines should have at least `amount`, `description`,
            `quantity`, `taxCode`, `number`. They are defined by the Avatax model `LineItemModel`.
            These lines can be built with the `_get_avatax_invoice_line` helper
        """
        raise NotImplementedError()  # implement in business document

    def _get_avatax_dates(self):
        """Get the dates related to the document.

        :return (tuple<date, date>): the document date and the tax computation date
        """
        raise NotImplementedError()  # implement in business document

    def _get_avatax_document_type(self):
        """Get the Avatax Document Type.

        Specifies the type of document to create. A document type ending with Invoice is a
        permanent transaction that will be recorded in AvaTax. A document type ending with Order is
        a temporary estimate that will not be preserved.

        :return (string): i.e. `SalesInvoice`, `ReturnInvoice` or `SalesOrder`
        """
        raise NotImplementedError()  # implement in business document

    def _get_avatax_ship_to_partner(self):
        """Get the customer's shipping address.

        This assumes that partner_id exists on models using this class.

        :return (Model): a `res.partner` record
        """
        return self.partner_shipping_id or self.partner_id

    # #############################################################################################
    # HELPERS
    # #############################################################################################

    def _get_avatax_invoice_line(self, product, price_subtotal, quantity, line_id):
        """Create a `LineItemModel` based on the parameters.

        :param product (Model<product.product>): product linked to the line
        :param price_subtotal (float): price tax excluded but discount included for all quantities
        :param quantity (float): quantity
        :param line_id: a unique identifier inside this transaction
        :return (dict): an Avatax model `LineItemModel`
        """
        if not product._get_avatax_category_id():
            raise UserError(_(
                'The Avalara Tax Code is required for %(name)s (#%(id)s)\n'
                'See https://taxcode.avatax.avalara.com/',
                name=product.display_name,
                id=product.id,
            ))
        item_code = product.code or ""
        if self.env.company.avalara_use_upc and product.barcode:
            item_code = f'UPC:{product.barcode}'
        return {
            'amount': price_subtotal,
            'description': product.display_name,
            'quantity': quantity,
            'taxCode': product._get_avatax_category_id().code,
            'itemCode': item_code,
            'number': line_id,
        }

    # #############################################################################################
    # PRIVATE UTILITIES
    # #############################################################################################

    def _get_avatax_ref(self):
        """Get a transaction reference."""
        return self.name or ''

    def _get_avatax_addresses(self, partner):
        """Get the addresses related to a partner.

        :param partner (Model<res.partner>): the partner we need the addresses of.
        :return (dict): the AddressesModel to return to Avatax
        """
        return {
            'shipTo': {
                'city': partner.city,
                'country': partner.country_id.code,
                'region': partner.state_id.code,
                'postalCode': partner.zip,
                'line1': partner.street,
            },
            'shipFrom': {
                'city': self.company_id.partner_id.city,
                'country': self.company_id.partner_id.country_id.code,
                'region': self.company_id.partner_id.state_id.code,
                'postalCode': self.company_id.partner_id.zip,
                'line1': self.company_id.partner_id.street,
            },
        }

    def _get_avatax_taxes(self, commit):
        """Get the transaction values.

        :param commit (bool): whether or not this transaction should be committed in Avatax.
        :return (dict): a mapping defined by the AvataxModel `CreateTransactionModel`.
        """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        document_date, tax_date = self._get_avatax_dates()
        taxes = {
            'addresses': self._get_avatax_addresses(self._get_avatax_ship_to_partner()),
            'companyCode': self.company_id.partner_id.avalara_partner_code or '',
            'customerCode': partner.avalara_partner_code or partner.avatax_unique_code,
            'entityUseCode': partner.with_company(self.company_id).avalara_exemption_id.code or '',
            'businessIdentificationNo': partner.vat or '',
            'date': (document_date or fields.Date.today()).isoformat(),
            'lines': self._get_avatax_invoice_lines(),
            'type': self._get_avatax_document_type(),
            'code': self.avatax_unique_code,
            'referenceCode': self._get_avatax_ref(),
            'currencyCode': self.currency_id.name or '',
            'commit': commit and self.company_id.avalara_commit,
        }

        if tax_date:
            taxes['taxOverride'] = {
                'type': 'taxDate',
                'reason': 'Manually changed the tax calculation date',
                'taxDate': tax_date.isoformat(),
            }

        return taxes

    def _query_avatax_taxes(self, commit):
        """Query Avatax with all the transactions linked to `self`.

        :param commit (bool): whether or not the transaction should be committed in Avatax.
        :return (dict<Model, dict>): a mapping between document records and the response from Avatax
        """
        if not self:
            return {}
        if not self.company_id.sudo().avalara_api_id or not self.company_id.sudo().avalara_api_key:
            raise RedirectWarning(
                _('Please add your AvaTax credentials'),
                self.env.ref('base_setup.action_general_configuration').id,
                _("Go to the configuration panel"),
            )
        client = self._get_client(self.company_id)
        transactions = {record: record._get_avatax_taxes(commit) for record in self}
        # TODO batch the `create_transaction`
        return {
            record: client.create_transaction(transaction, include='Lines')
            for record, transaction in transactions.items()
        }

    # #############################################################################################
    # PUBLIC UTILITIES
    # #############################################################################################

    def _map_avatax(self, commit):
        """Link Avatax response to Odoo's models.

        :param commit (bool): whether or not the transaction should be committed in Avatax.
        :return (tuple(detail, summary)):
            detail (dict<Model, Model<account.tax>>): mapping between the document lines and its
                related taxes.
            summary (dict<Model, dict<Model<account.tax>, float>>): mapping between each tax and
                the total computed amount, for each document.
        """
        def find_or_create_tax(doc, detail):
            def repartition_line(repartition_type, account=None):
                return (0, 0, {
                    'repartition_type': repartition_type,
                    'tag_ids': [],
                    'company_id': doc.company_id.id,
                    'account_id': account and account.id,
                })
            # 4 precision digits is the same as is used on the amount field of account.tax
            name_precision = 4
            tax_name = '%s [%s] (%s %%)' % (
                detail['taxName'],
                detail['jurisCode'],
                float_repr(float_round(detail['rate'] * 100, name_precision), name_precision),
            )
            key = (tax_name, doc.company_id)
            if key not in tax_cache:
                tax_cache[key] = self.env['account.tax'].search([
                    ('name', '=', tax_name),
                    ('company_id', '=', doc.company_id.id),
                ]) or self.env['account.tax'].sudo().with_company(doc.company_id).create({
                    'name': tax_name,
                    'amount': detail['rate'] * 100,
                    'amount_type': 'percent',
                    'refund_repartition_line_ids': [
                        repartition_line('base'),
                        repartition_line('tax', doc.fiscal_position_id.avatax_refund_account_id),
                    ],
                    'invoice_repartition_line_ids': [
                        repartition_line('base'),
                        repartition_line('tax', doc.fiscal_position_id.avatax_invoice_account_id),
                    ],
                })
            return tax_cache[key]
        tax_cache = {}

        query_results = self._query_avatax_taxes(commit)
        details, summary = {}, {}
        errors = []
        for document, query_result in query_results.items():
            error = self._handle_response(query_result, _(
                'Odoo could not fetch the taxes related to %(document)s.\n'
                'Please check the status of `%(technical)s` in the AvaTax portal.',
                document=document.display_name,
                technical=document.avatax_unique_code,
            ))
            if error:
                errors.append(error)
        if errors:
            raise UserError('\n\n'.join(errors))

        for document, query_result in query_results.items():
            for line_result in query_result['lines']:
                record_id = line_result['lineNumber'].split(',')
                record = self.env[record_id[0]].browse(int(record_id[1]))
                details.setdefault(record, {})
                details[record]['total'] = line_result['lineAmount']
                details[record]['tax_amount'] = line_result['tax']
                for detail in line_result['details']:
                    tax = find_or_create_tax(document, detail)
                    details[record].setdefault('tax_ids', self.env['account.tax'])
                    details[record]['tax_ids'] += tax

            summary[document] = {}
            for summary_line in query_result['summary']:
                tax = find_or_create_tax(document, summary_line)
                summary[document][tax] = summary_line['tax']

        return details, summary

    def _uncommit_avatax_transaction(self):
        """ Uncommit a transaction in Avatax.

        Uncommit the transaction linked to this document.
        """
        for record in self:
            if not record.company_id.avalara_commit:
                continue
            client = self._get_client(record.company_id)
            query_result = client.uncommit_transaction(
                companyCode=record.company_id.partner_id.avalara_partner_code,
                transactionCode=self.avatax_unique_code,
            )
            error = self._handle_response(query_result, _(
                'Odoo could not change the state of the transaction related to %(document)s in'
                ' AvaTax\nPlease check the status of `%(technical)s` in the AvaTax portal.',
                document=record.display_name,
                technical=record.avatax_unique_code,
            ))
            if error:
                raise UserError(error)

    def _void_avatax_transaction(self):
        for record in self:
            if not record.company_id.avalara_commit:
                continue
            client = self._get_client(record.company_id)
            query_result = client.void_transaction(
                companyCode=record.company_id.partner_id.avalara_partner_code,
                transactionCode=self.avatax_unique_code,
                model={"code": "DocVoided"},
            )

            # There's nothing to void when a draft record is deleted without ever being sent to Avatax.
            if query_result.get('error', {}).get('code') == 'EntityNotFoundError':
                logger.info(pformat(query_result))
                continue

            error = self._handle_response(query_result, _(
                'Odoo could not void the transaction related to %(document)s in AvaTax\nPlease '
                'check the status of `%(technical)s` in the AvaTax portal.',
                document=record.display_name,
                technical=record.avatax_unique_code,
            ))
            if error:
                raise UserError(error)

    # #############################################################################################
    # COMMUNICATION
    # #############################################################################################

    def _handle_response(self, response, title):
        if response.get('errors'):  # http error
            logger.warning(pformat(response), stack_info=True)
            return '%s\n%s' % (title, _(
                '%(response)s',
                response=response.get('title', ''),
            ))
        if response.get('error'):  # avatax error
            logger.warning(pformat(response), stack_info=True)
            messages = '\n'.join(detail['message'] for detail in response['error']['details'])
            return '%s\n%s' % (title, messages)

    def _get_client(self, company):
        client = AvataxClient(
            app_name='Odoo',
            app_version=version,
            environment=company.avalara_environment,
        )
        client.add_credentials(
            company.sudo().avalara_api_id or '',
            company.sudo().avalara_api_key or '',
        )
        log_end_date = self.env['ir.config_parameter'].sudo().get_param(
            'account_avatax.log.end.date', ''
        )
        try:
            log_end_date = datetime.strptime(log_end_date, DEFAULT_SERVER_DATETIME_FORMAT)
            need_log = fields.Datetime.now() < log_end_date
        except ValueError:
            need_log = False
        if need_log:
            def logger(message):
                ''' This creates a new cursor to make sure the log is committed even when an
                    exception is thrown later in this request.
                '''
                self.env.flush_all()
                dbname = self._cr.dbname
                with registry(dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    env['ir.logging'].create({
                        'name': 'Avatax',
                        'type': 'server',
                        'level': 'INFO',
                        'dbname': dbname,
                        'message': message,
                        'func': '',
                        'path': '',
                        'line': '',
                    })
            client.logger = logger
        return client
