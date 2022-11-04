# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import re

from datetime import datetime
from io import BytesIO
from markupsafe import Markup
from psycopg2 import OperationalError

from lxml import etree

from odoo import fields, models
from odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util import UnexpectedXMLResponse, InvalidToken
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_repr

_logger = logging.getLogger(__name__)

try:
    import pdf417gen
except ImportError:
    pdf417gen = None
    _logger.error('Could not import library pdf417gen')


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['l10n_cl.edi.util', 'account.move']

    l10n_cl_sii_barcode = fields.Char(
        string='SII Barcode', readonly=True, copy=False,
        help='This XML contains the portion of the DTE XML that should be coded in PDF417 '
             'and printed in the invoice barcode should be present in the printed invoice report to be valid')
    l10n_cl_dte_status = fields.Selection([
        ('not_sent', 'Pending To Be Sent'),
        ('ask_for_status', 'Ask For Status'),
        ('accepted', 'Accepted'),
        ('objected', 'Accepted With Objections'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('manual', 'Manual'),
    ], string='SII DTE status', copy=False, tracking=True, help="""Status of sending the DTE to the SII:
    - Not sent: the DTE has not been sent to SII but it has created.
    - Ask For Status: The DTE is asking for its status to the SII.
    - Accepted: The DTE has been accepted by SII.
    - Accepted With Objections: The DTE has been accepted with objections by SII.
    - Rejected: The DTE has been rejected by SII.
    - Cancelled: The DTE has been deleted by the user.
    - Manual: The DTE is sent manually, i.e.: the DTE will not be sending manually.""")
    l10n_cl_dte_partner_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent'),
    ], string='Partner DTE status', copy=False, readonly=True, help="""
    Status of sending the DTE to the partner:
    - Not sent: the DTE has not been sent to the partner but it has sent to SII.
    - Sent: The DTE has been sent to the partner.""")
    l10n_cl_dte_acceptation_status = fields.Selection([
        ('received', 'Received'),
        ('ack_sent', 'Acknowledge Sent'),
        ('claimed', 'Claimed'),
        ('accepted', 'Accepted'),
    ], string='DTE Accept status', copy=False, help="""The status of the DTE Acceptation
    Received: the DTE was received by us for vendor bills, by our customers for customer invoices.
    Acknowledge Sent: the Acknowledge has been sent to the vendor.
    Claimed: the DTE was claimed by us for vendor bills, by our customers for customer invoices.
    Accepted: the DTE was accepted by us for vendor bills, by our customers for customer invoices.
    """)
    l10n_cl_claim = fields.Selection([
        ('ACD', 'Accept the Content of the Document'),
        ('RCD', 'Claim the Content of the Document'),
        ('ERM', 'Provide Receipt of Merchandise or Services'),
        ('RFP', 'Claim for Partial Lack of Merchandise'),
        ('RFT', 'Claim for Total Lack of Merchandise'),
    ], string='Claim', copy=False, help='The reason why the DTE was accepted or claimed by the customer')
    l10n_cl_claim_description = fields.Char(string='Claim Detail', readonly=True, copy=False)
    l10n_cl_sii_send_file = fields.Many2one('ir.attachment', string='SII Send file', copy=False)
    l10n_cl_dte_file = fields.Many2one('ir.attachment', string='DTE file', copy=False)
    l10n_cl_sii_send_ident = fields.Text(string='SII Send Identification(Track ID)', readonly=True,
                                         states={'draft': [('readonly', False)]}, copy=False, tracking=True)
    l10n_cl_journal_point_of_sale_type = fields.Selection(related='journal_id.l10n_cl_point_of_sale_type')
    l10n_cl_reference_ids = fields.One2many('l10n_cl.account.invoice.reference', 'move_id', readonly=True,
                                            states={'draft': [('readonly', False)]}, string='Reference Records')

    def button_cancel(self):
        for record in self.filtered(lambda x: x.company_id.country_id.code == "CL"):
            # The move cannot be modified once the DTE has been accepted, objected or sent to the SII
            if record.l10n_cl_dte_status in ['accepted', 'objected']:
                l10n_cl_dte_status = dict(record._fields['l10n_cl_dte_status']._description_selection(
                    self.env)).get(record.l10n_cl_dte_status)
                raise UserError(_('This %s is in SII status: %s. It cannot be cancelled. '
                                  'Instead you should revert it.') % (
                    record.l10n_latam_document_type_id.name, l10n_cl_dte_status))
            elif record.l10n_cl_dte_status == 'ask_for_status':
                raise UserError(_('This %s is in the intermediate state: \'Ask for Status in the SII\'. '
                                  'You will be able to cancel it only when the document has reached the state '
                                  'of rejection. Otherwise, if it were accepted or objected you should revert it '
                                  'with a suitable document instead of cancelling it.') %
                                record.l10n_latam_document_type_id.name)
            record.l10n_cl_dte_status = 'cancelled'
        return super().button_cancel()

    def button_draft(self):
        for record in self.filtered(lambda x: x.company_id.country_id.code == "CL"):
            # The move cannot be modified once the DTE has been accepted, objected or sent to the SII
            if record.l10n_cl_dte_status in ['accepted', 'objected']:
                l10n_cl_dte_status = dict(record._fields['l10n_cl_dte_status']._description_selection(
                    self.env)).get(record.l10n_cl_dte_status)
                raise UserError(_('This %s is in SII status %s. It cannot be reset to draft state. '
                                  'Instead you should revert it.') % (
                    record.l10n_latam_document_type_id.name, l10n_cl_dte_status))
            elif record.l10n_cl_dte_status == 'ask_for_status':
                raise UserError(_('This %s is in the intermediate state: \'Ask for Status in the SII\'. '
                                  'You will be able to reset it to draft only when the document has reached the state '
                                  'of rejection. Otherwise, if it were accepted or objected you should revert it '
                                  'with a suitable document instead of cancelling it.') %
                                record.l10n_latam_document_type_id.name)
            record.l10n_cl_dte_status = None
        return super().button_draft()

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        # Avoid to post a vendor bill with a inactive currency created from the incoming mail
        for move in self.filtered(
                lambda x: x.company_id.account_fiscal_country_id.code == "CL" and
                          x.company_id.l10n_cl_dte_service_provider in ['SII', 'SIITEST'] and
                          x.journal_id.l10n_latam_use_documents):
            # check if we have the currency active, in order to receive vendor bills correctly.
            if move.move_type in ['in_invoice', 'in_refund'] and not move.currency_id.active:
                raise UserError(
                    _('Invoice %s has the currency %s inactive. Please activate the currency and try again.') % (
                        move.name, move.currency_id.name))
            # generation of customer invoices
            if ((move.move_type in ['out_invoice', 'out_refund'] and move.journal_id.type == 'sale')
                    or (move.move_type in ['in_invoice', 'in_refund'] and move.l10n_latam_document_type_id._is_doc_type_vendor())):
                if move.journal_id.l10n_cl_point_of_sale_type != 'online' and not move.l10n_latam_document_type_id._is_doc_type_vendor():
                    move.l10n_cl_dte_status = 'manual'
                    continue
                move._l10n_cl_edi_post_validation()
                move._l10n_cl_create_dte()
                move.l10n_cl_dte_status = 'not_sent'
                dte_signed, file_name = move._l10n_cl_create_dte_envelope()
                attachment = self.env['ir.attachment'].create({
                    'name': 'SII_{}'.format(file_name),
                    'res_id': move.id,
                    'res_model': 'account.move',
                    'datas': base64.b64encode(dte_signed.encode('ISO-8859-1', 'replace')),
                    'type': 'binary',
                })
                move.l10n_cl_sii_send_file = attachment.id
                move.with_context(no_new_invoice=True).message_post(
                    body=_('DTE has been created'),
                    attachment_ids=attachment.ids)
        return res

    def action_reverse(self):
        for record in self.filtered(lambda x: x.company_id.account_fiscal_country_id.code == "CL"):
            if record.l10n_cl_dte_status == 'rejected':
                raise UserError(_('This %s is rejected by SII. Instead of creating a reverse, you should set it to '
                                  'draft state, correct it and post it again.') %
                                record.l10n_latam_document_type_id.name)
        return super().action_reverse()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super(AccountMove, self)._reverse_moves(default_values_list, cancel)
        # The reverse move lines of the reverse moves created to correct the original text are replaced by
        # a line with the quantity to 1, the amount to 0 and the original text and correct text as the name
        # since sii regulations stipulate the option to use this kind of document with an amount_untaxed
        # and amount_total equal to $0.0 just in order to inform this is only a text correction.
        # for example, for a bad address or a bad activity description in the originating document.
        if self._context.get('default_l10n_cl_edi_reference_doc_code') == '2':
            for move in reverse_moves:
                move.invoice_line_ids = [[5, 0], [0, 0, {
                    'account_id': move.journal_id.default_account_id.id,
                    'name': _('Where it says: %s should say: %s') % (
                        self._context.get('default_l10n_cl_original_text'),
                        self._context.get('default_l10n_cl_corrected_text')),
                    'quantity': 1,
                    'price_unit': 0.0,
                }, ], ]
        return reverse_moves

    # SII Customer Invoice Buttons

    def _l10n_cl_send_dte_reception_status(self, status_type):
        """
        Send to the supplier the acceptance or claim of the bill received.
        """
        response_id = self.env['ir.sequence'].browse(self.env.ref('l10n_cl_edi.response_sequence').id).next_by_id()
        response = self.env['ir.qweb']._render('l10n_cl_edi.response_dte', {
            'move': self,
            'format_vat': self._l10n_cl_format_vat,
            'time_stamp': self._get_cl_current_strftime(),
            'response_id': response_id,
            'dte_status': 2 if status_type == 'claimed' else 0,
            'dte_glosa_status': 'DTE Rechazado' if status_type == 'claimed' else 'DTE Aceptado OK',
            'code_rejected': '-1' if status_type == 'claimed' else None,
            '__keep_empty_lines': True,
        })
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        signed_response = self._sign_full_xml(
            response, digital_signature, '', 'env_resp', self.l10n_latam_document_type_id._is_doc_type_voucher())
        dte_attachment = self.env['ir.attachment'].create({
            'name': 'DTE_{}.xml'.format(self.name),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(bytes(signed_response, 'utf-8')),
        })
        self.l10n_cl_dte_file = dte_attachment.id
        email_template = (self.env.ref('l10n_cl_edi.email_template_claimed_ack') if status_type == 'claimed' else
                          self.env.ref('l10n_cl_edi.email_template_receipt_commercial_accept'))
        email_template.send_mail(self.id, force_send=True, email_values={'attachment_ids': [dte_attachment.id]})

    def l10n_cl_send_dte_to_sii(self, retry_send=True):
        """
        Send the DTE to the SII.
        """
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute('SELECT * FROM account_move WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])
        except OperationalError as e:
            if e.pgcode == '55P03':
                if not self.env.context.get('cron_skip_connection_errs'):
                    raise UserError(_('This invoice is being processed already.'))
                return
            raise e
        # To avoid double send on double-click
        if self.l10n_cl_dte_status != "not_sent":
            return None
        _logger.info('Sending DTE for invoice with ID %s (name: %s)', self.id, self.name)
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        response = self._send_xml_to_sii(
            self.company_id.l10n_cl_dte_service_provider,
            self.company_id.website,
            self.company_id.vat,
            self.l10n_cl_sii_send_file.name,
            base64.b64decode(self.l10n_cl_sii_send_file.datas),
            digital_signature
        )
        if not response:
            return None

        response_parsed = etree.fromstring(response)
        self.l10n_cl_sii_send_ident = response_parsed.findtext('TRACKID')
        sii_response_status = response_parsed.findtext('STATUS')
        if sii_response_status == '5':
            digital_signature.last_token = False
            _logger.error('The response status is %s. Clearing the token.' %
                          self._l10n_cl_get_sii_reception_status_message(sii_response_status))
            if retry_send:
                _logger.info('Retrying send DTE to SII')
                self.l10n_cl_send_dte_to_sii(retry_send=False)

            # cleans the token and keeps the l10n_cl_dte_status until new attempt to connect
            # would like to resend from here, because we cannot wait till tomorrow to attempt
            # a new send
        else:
            self.l10n_cl_dte_status = 'ask_for_status' if sii_response_status == '0' else 'rejected'
        self.message_post(body=_('DTE has been sent to SII with response: %s.') %
                               self._l10n_cl_get_sii_reception_status_message(sii_response_status))

    def l10n_cl_verify_dte_status(self, send_dte_to_partner=True):
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        response = self._get_send_status(
            self.company_id.l10n_cl_dte_service_provider,
            self.l10n_cl_sii_send_ident,
            self._l10n_cl_format_vat(self.company_id.vat),
            digital_signature)
        if not response:
            self.l10n_cl_dte_status = 'ask_for_status'
            digital_signature.last_token = False
            return None

        response_parsed = etree.fromstring(response.encode('utf-8'))

        if response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO') in ['001', '002', '003']:
            digital_signature.last_token = False
            _logger.error('Token is invalid.')
            return

        try:
            self.l10n_cl_dte_status = self._analyze_sii_result(response_parsed)
        except UnexpectedXMLResponse:
            # The assumption here is that the unexpected input is intermittent,
            # so we'll retry later. If the same input appears regularly, it should
            # be handled properly in _analyze_sii_result.
            _logger.error("Unexpected XML response:\n%s", response)
            return

        if self.l10n_cl_dte_status in ['accepted', 'objected']:
            self.l10n_cl_dte_partner_status = 'not_sent'
            if send_dte_to_partner:
                self._l10n_cl_send_dte_to_partner()

        self.message_post(
            body=_('Asking for DTE status with response:') +
                 '<br /><li><b>ESTADO</b>: %s</li><li><b>GLOSA</b>: %s</li><li><b>NUM_ATENCION</b>: %s</li>' % (
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO'),
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/GLOSA'),
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/NUM_ATENCION')))

    def l10n_cl_verify_claim_status(self):
        if self.company_id.l10n_cl_dte_service_provider == 'SIITEST':
            raise UserError(_('This feature is not available in certification/test mode'))
        response = self._get_dte_claim(
            self.company_id.l10n_cl_dte_service_provider,
            self.company_id.vat,
            self.company_id._get_digital_signature(user_id=self.env.user.id),
            self.l10n_latam_document_type_id.code,
            self.l10n_latam_document_number
        )
        if not response:
            return None

        try:
            response_code = response['listaEventosDoc']['codEvento']
        except Exception as error:
            _logger.error(error)
            if not self.env.context.get('cron_skip_connection_errs'):
                self.message_post(body=_('Asking for claim status with response:') + '<br/>: %s <br/>' % response +
                                       _('failed due to:') + '<br/> %s' % error)
        else:
            self.l10n_cl_claim = response_code
            self.message_post(body=_('Asking for claim status with response:') + '<br/> %s' % response)

    # SII Vendor Bills Buttons

    def l10n_cl_reprocess_acknowledge(self):
        if not self.partner_id:
            raise UserError(_('Please assign a partner before sending the acknowledgement'))
        try:
            self._l10n_cl_send_receipt_acknowledgment()
        except Exception as error:
            self.message_post(body=error)

    def _l10n_cl_send_receipt_acknowledgment(self):
        """
        This method sends an xml with the acknowledgement of the reception of the invoice
        by email to the vendor.
        """
        attch_name = 'DTE_{}.xml'.format(self.l10n_latam_document_number)
        dte_attachment = self.l10n_cl_dte_file
        if not dte_attachment:
            raise Exception(_('DTE attachment not found => %s') % attch_name)
        xml_dte = base64.b64decode(dte_attachment.datas).decode('utf-8')
        xml_content = etree.fromstring(xml_dte)
        response_id = self.env['ir.sequence'].browse(self.env.ref('l10n_cl_edi.response_sequence').id).next_by_id()
        xml_ack_template = self.env['ir.qweb']._render('l10n_cl_edi.ack_template', {
            'move': self,
            'format_vat': self._l10n_cl_format_vat,
            'get_cl_current_strftime': self._get_cl_current_strftime,
            'response_id': response_id,
            'nmb_envio': 'RESP_%s' % attch_name,
            'envio_dte_id': self._l10n_cl_get_set_dte_id(xml_content),
            'digest_value': xml_content.findtext(
                './/ns1:DigestValue', namespaces={'ns1': 'http://www.w3.org/2000/09/xmldsig#'}),
            '__keep_empty_lines': True,
        })
        xml_ack_template = xml_ack_template.replace(
            '&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace(
            '<?xml version="1.0" encoding="ISO-8859-1" ?>', '')
        try:
            digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        except Exception:
            raise Exception(_('There is no signature available to send acknowledge or acceptation of this DTE. '
                              'Please setup your digital signature'))
        xml_ack = self._sign_full_xml(xml_ack_template, digital_signature, str(response_id),
                                      'env_resp', self.l10n_latam_document_type_id._is_doc_type_voucher())
        attachment = self.env['ir.attachment'].create({
            'name': 'receipt_acknowledgment_{}.xml'.format(response_id),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(bytes(xml_ack, 'utf-8')),
        })
        self.env.ref('l10n_cl_edi.email_template_receipt_ack').send_mail(self.id, force_send=True, email_values={
            'attachment_ids': attachment})
        self.l10n_cl_dte_acceptation_status = 'ack_sent'

    def l10n_cl_accept_document(self):
        if not self.l10n_latam_document_type_id._is_doc_type_acceptance():
            raise UserError(_('The document type with code %s cannot be accepted') %
                            self.l10n_latam_document_type_id.code)
        if self.company_id.l10n_cl_dte_service_provider == 'SIITEST':
            self._l10n_cl_send_dte_reception_status('accepted')
            self.l10n_cl_dte_acceptation_status = 'accepted'
            self.message_post(body=_('Claim status was not sending to SII. This feature is not available in '
                                     'certification/test mode'))
            return None
        try:
            response = self._send_sii_claim_response(
                self.company_id.l10n_cl_dte_service_provider, self.partner_id.vat,
                self.company_id._get_digital_signature(user_id=self.env.user.id), self.l10n_latam_document_type_id.code,
                self.l10n_latam_document_number, 'ACD')
        except InvalidToken:
            digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
            digital_signature.last_token = None
            return self.l10n_cl_accept_document()
        if not response:
            return None

        try:
            cod_response = response['codResp']
        except Exception as error:
            _logger.error(error)
            self.message_post(body=_('Exception error parsing the response: %s') % response)
            return None
        if cod_response in [0, 1]:
            self.l10n_cl_dte_acceptation_status = 'accepted'
            self._l10n_cl_send_dte_reception_status('accepted')
            msg = _('Document acceptance was accepted with response:') + '<br/> %s' % response
        else:
            msg = _('Document acceptance failed with response:') + '<br/> %s' % response
        self.message_post(body=msg)

    def l10n_cl_claim_document(self):
        if not self.l10n_latam_document_type_id._is_doc_type_acceptance():
            raise UserError(_('The document type with code %s cannot be claimed') %
                            self.l10n_latam_document_type_id.code)
        if self.company_id.l10n_cl_dte_service_provider == 'SIITEST':
            self._l10n_cl_send_dte_reception_status('claimed')
            self.write({
                'l10n_cl_dte_acceptation_status': 'claimed',
                'state': 'cancel',
            })
            self.message_post(body=_('The claim status was not sent to SII as this feature does not work '
                                     'in certification/test mode'))
            return
        try:
            response = self._send_sii_claim_response(
                self.company_id.l10n_cl_dte_service_provider,
                self.partner_id.vat,
                self.company_id._get_digital_signature(user_id=self.env.user.id),
                self.l10n_latam_document_type_id.code,
                self.l10n_latam_document_number,
                'RCD'
            )
        except InvalidToken:
            digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
            digital_signature.last_token = None
            return self.l10n_cl_claim_document()
        if not response:
            return None
        try:
            cod_response = response['codResp']
        except Exception as error:
            _logger.error(error)
            self.message_post(body='Exception error parsing the response: %s' % response)
        else:
            if cod_response in [0, 1]:
                self.write({
                    'l10n_cl_dte_acceptation_status': 'claimed',
                    'state': 'cancel',
                })
                self._l10n_cl_send_dte_reception_status('claimed')
                msg = _('Document was claimed with response:') + '<br/> %s' % response
            else:
                msg = _('Document claim failed with response:') + '<br/> %s' % response
            self.message_post(body=msg)

    # DTE creation

    def _l10n_cl_create_dte(self):
        folio = int(self.l10n_latam_document_number)
        doc_id_number = 'F{}T{}'.format(folio, self.l10n_latam_document_type_id.code)
        dte_barcode_xml = self._l10n_cl_get_dte_barcode_xml()
        self.l10n_cl_sii_barcode = dte_barcode_xml['barcode']
        dte = self.env['ir.qweb']._render('l10n_cl_edi.dte_template', {
            'move': self,
            'format_vat': self._l10n_cl_format_vat,
            'get_cl_current_strftime': self._get_cl_current_strftime,
            'format_length': self._format_length,
            'format_uom': self._format_uom,
            'float_repr': float_repr,
            'doc_id': doc_id_number,
            'caf': self.l10n_latam_document_type_id._get_caf_file(self.company_id.id, int(self.l10n_latam_document_number)),
            'amounts': self._l10n_cl_get_amounts(),
            'withholdings': self._l10n_cl_get_withholdings(),
            'dte': dte_barcode_xml['ted'],
            '__keep_empty_lines': True,
        })
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        signed_dte = self._sign_full_xml(
            dte, digital_signature, doc_id_number, 'doc', self.l10n_latam_document_type_id._is_doc_type_voucher())
        dte_attachment = self.env['ir.attachment'].create({
            'name': 'DTE_{}.xml'.format(self.name),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(signed_dte.encode('ISO-8859-1', 'replace'))
        })
        self.l10n_cl_dte_file = dte_attachment.id

    def _l10n_cl_create_partner_dte(self):
        dte_signed, file_name = self._l10n_cl_create_dte_envelope(
            '55555555-5' if self.partner_id.l10n_cl_sii_taxpayer_type == '4' else self.partner_id.vat)
        dte_partner_attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(dte_signed.encode('ISO-8859-1', 'replace'))
        })
        self.with_context(no_new_invoice=True).message_post(
            body=_('Partner DTE has been generated'),
            attachments_ids=[dte_partner_attachment.id])
        return dte_partner_attachment

    def _l10n_cl_create_dte_envelope(self, receiver_rut='60803000-K'):
        file_name = 'F{}T{}.xml'.format(self.l10n_latam_document_number, self.l10n_latam_document_type_id.code)
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        template = self.l10n_latam_document_type_id._is_doc_type_voucher() and self.env.ref(
            'l10n_cl_edi.envio_boleta') or self.env.ref('l10n_cl_edi.envio_dte')
        dte = self.l10n_cl_dte_file.raw.decode('ISO-8859-1')
        dte = Markup(dte.replace('<?xml version="1.0" encoding="ISO-8859-1" ?>', ''))
        dte_rendered = self.env['ir.qweb']._render(template.id, {
            'move': self,
            'RutEmisor': self._l10n_cl_format_vat(self.company_id.vat),
            'RutEnvia': digital_signature.subject_serial_number,
            'RutReceptor': receiver_rut,
            'FchResol': self.company_id.l10n_cl_dte_resolution_date,
            'NroResol': self.company_id.l10n_cl_dte_resolution_number,
            'TmstFirmaEnv': self._get_cl_current_strftime(),
            'dte': dte,
            '__keep_empty_lines': True,
        })
        dte_rendered = dte_rendered.replace('<?xml version="1.0" encoding="ISO-8859-1" ?>', '')
        dte_signed = self._sign_full_xml(
            dte_rendered, digital_signature, 'SetDoc',
            self.l10n_latam_document_type_id._is_doc_type_voucher() and 'bol' or 'env',
            self.l10n_latam_document_type_id._is_doc_type_voucher()
        )
        return dte_signed, file_name

    # DTE sending

    def _l10n_cl_send_dte_to_partner(self):
        # We need a DTE with the partner vat as RutReceptor to be sent to the partner
        dte_partner_attachment = self._l10n_cl_create_partner_dte()
        self.env.ref('l10n_cl_edi.l10n_cl_edi_email_template_invoice').send_mail(
            self.id, force_send=True, email_values={'attachment_ids': [dte_partner_attachment.id]})
        self.l10n_cl_dte_partner_status = 'sent'
        self.message_post(body=_('DTE has been sent to the partner'))

    # Helpers

    def _l10n_cl_edi_currency_validation(self):
        if self.currency_id != self.company_id.currency_id and self.l10n_cl_journal_point_of_sale_type == 'online':
            return self.l10n_latam_document_type_id._is_doc_type_export()
        return True

    def _l10n_cl_edi_post_validation(self):
        if not self._l10n_cl_edi_currency_validation():
            raise UserError(
                _('It is not possible to validate invoices in %s for %s, please convert it to CLP') % (
                    self.currency_id.name, self.l10n_latam_document_type_id.name))
        if (self.l10n_cl_journal_point_of_sale_type == 'online' and
                not ((self.partner_id.l10n_cl_dte_email or self.commercial_partner_id.l10n_cl_dte_email) and
                     self.company_id.l10n_cl_dte_email) and
                not self.l10n_latam_document_type_id._is_doc_type_export() and
                not self.l10n_latam_document_type_id._is_doc_type_ticket()):
            raise UserError(_('The %s %s has not a DTE email defined. This is mandatory for electronic invoicing.') %
                            (_('partner') if not (self.partner_id.l10n_cl_dte_email or
                                                  self.commercial_partner_id.l10n_cl_dte_email) else _('company'), self.partner_id.name))
        if datetime.strptime(self._get_cl_current_strftime(), '%Y-%m-%dT%H:%M:%S').date() < self.invoice_date:
            raise UserError(
                _('The stamp date and time cannot be prior to the invoice issue date and time. TIP: check '
                  'in your user preferences if the timezone is "America/Santiago"'))
        if not self.company_id.l10n_cl_dte_service_provider:
            raise UserError(_(
                'You have not selected an invoicing service provider for your company. '
                'Please go to your company and select one'))
        if not self.company_id.l10n_cl_activity_description:
            raise UserError(_(
                'Your company has not an activity description configured. This is mandatory for electronic '
                'invoicing. Please go to your company and set the correct one (www.sii.cl - Mi SII)'))
        if not self.company_id.l10n_cl_company_activity_ids:
            raise UserError(_(
                'There are no activity codes configured in your company. This is mandatory for electronic '
                'invoicing. Please go to your company and set the correct activity codes (www.sii.cl - Mi SII)'))
        if not self.company_id.l10n_cl_sii_regional_office:
            raise UserError(_(
                'There is no SII Regional Office configured in your company. This is mandatory for electronic '
                'invoicing. Please go to your company and set the regional office, according to your company '
                'address (www.sii.cl - Mi SII)'))
        if (self.l10n_latam_document_type_id.code not in ['39', '41', '110', '111', '112'] and
                not (self.partner_id.l10n_cl_activity_description or
                     self.commercial_partner_id.l10n_cl_activity_description)):
            raise UserError(_(
                'There is not an activity description configured in the '
                'customer %s record. This is mandatory for electronic invoicing for this type of '
                'document. Please go to the partner record and set the activity description') % self.partner_id.name)
        if not self.l10n_latam_document_type_id._is_doc_type_electronic_ticket() and not self.partner_id.street:
            raise UserError(_(
                'There is no address configured in your customer %s record. '
                'This is mandatory for electronic invoicing for this type of document. '
                'Please go to the partner record and set the address') % self.partner_id.name)
        if (self.l10n_latam_document_type_id.code in ['34', '41', '110', '111', '112'] and
                self.amount_untaxed != self.amount_total):
            raise UserError(_('It seems that you are using items with taxes in exempt documents in invoice %s - %s.'
                              ' You must either:\n'
                              '   - Change the document type to a not exempt type.\n'
                              '   - Set an exempt fiscal position to remove taxes automatically.\n'
                              '   - Use products without taxes.\n'
                              '   - Remove taxes from product lines.') % (self.id, self.name))
        if self.l10n_latam_document_type_id.code == '33' and self.amount_untaxed == self.amount_total:
            raise UserError(_('All the items you are billing in invoice %s - %s, have no taxes.\n'
                              ' If you need to bill exempt items you must either use exempt invoice document type (34),'
                              ' or at least one of the items should have vat tax.') % (self.id, self.name))

        self._l10n_cl_edi_validate_boletas()

    def _l10n_cl_edi_validate_boletas(self):
        if self.l10n_latam_document_type_id.code in ['39', '41']:
            raise UserError(_('Ticket is not allowed, please contact your administrator to install the '
                            'l10n_cl_edi_boletas module'))

    def _l10n_cl_get_sii_reception_status_message(self, sii_response_status):
        """
        Get the value of the code returns by SII once the DTE has been sent to the SII.
        """
        return {
            '0': _('Upload OK'),
            '1': _('Sender Does Not Have Permission To Send'),
            '2': _('File Size Error (Too Big or Too Small)'),
            '3': _('Incomplete File (Size <> Parameter size)'),
            '5': _('Not Authenticated'),
            '6': _('Company Not Authorized to Send Files'),
            '7': _('Invalid Schema'),
            '8': _('Document Signature'),
            '9': _('System Locked'),
            'Otro': _('Internal Error'),
        }.get(sii_response_status, sii_response_status)

    def _l10n_cl_get_amounts(self):
        """
        This method is used to calculate the amount and taxes required in the Chilean localization electronic documents.
        """
        self.ensure_one()
        vat_taxes = self.line_ids.filtered(lambda x: x.tax_line_id.l10n_cl_sii_code == 14)
        lines_with_taxes = self.invoice_line_ids.filtered(lambda x: x.tax_ids)
        lines_without_taxes = self.invoice_line_ids.filtered(lambda x: not x.tax_ids)
        values = {
            'vat_amount': self.direction_sign * self.currency_id.round(sum(vat_taxes.mapped('amount_currency'))),
            # Sum of the subtotal amount affected by tax
            'subtotal_amount_taxable': sum(lines_with_taxes.mapped('price_subtotal')) if (
                    lines_with_taxes and (self.l10n_latam_document_type_id.code == '39' or
                    not self.l10n_latam_document_type_id._is_doc_type_voucher())) else False,
            # Sum of the subtotal amount not affected by tax
            'subtotal_amount_exempt': sum(lines_without_taxes.mapped('price_subtotal')) if lines_without_taxes else False,
            'vat_percent': (
                '%.2f' % (vat_taxes[0].tax_line_id.mapped('amount')[0])
                if vat_taxes and (self.l10n_latam_document_type_id.code == '39' or not
                self.l10n_latam_document_type_id._is_doc_type_voucher()) and
                   not self.l10n_latam_document_type_id._is_doc_type_exempt() else False
            ),
            'total_amount': self.currency_id.round(self.amount_total),
        }
        # Calculate the fields needed if the invoice has a different currency than company currency
        if self.currency_id != self.company_id.currency_id and self.l10n_latam_document_type_id._is_doc_type_export():
            rate = (self.currency_id + self.company_id.currency_id)._get_rates(self.company_id, self.date).get(
                self.currency_id.id) or 1
            values['second_currency'] = {'rate': rate}

            values['second_currency'].update({
                'subtotal_amount_taxable': sum(lines_with_taxes.mapped('price_subtotal')) / rate if lines_with_taxes else False,
                'subtotal_amount_exempt': sum(lines_without_taxes.mapped('price_subtotal')) / rate if lines_without_taxes else False,
                'vat_amount': sum(lines_with_taxes.mapped('price_subtotal')) / rate if lines_with_taxes else False,
                'total_amount': self.amount_total / rate
            })
        return values

    def _l10n_cl_get_withholdings(self):
        """
        This method calculates the section of withholding taxes, or 'other' taxes for the Chilean electronic invoices.
        These taxes are not VAT taxes in general; they are special taxes (for example, alcohol or sugar-added beverages,
        withholdings for meat processing, fuel, etc.
        The taxes codes used are included here:
        [15, 17, 18, 19, 24, 25, 26, 27, 271]
        http://www.sii.cl/declaraciones_juradas/ddjj_3327_3328/cod_otros_imp_retenc.pdf
        The need of the tax is not just the amount, but the code of the tax, the percentage amount and the amount
        :return:
        """
        self.ensure_one()
        return [{'tax_code': line.tax_line_id.l10n_cl_sii_code,
                 'tax_percent': abs(line.tax_line_id.amount),
                 'tax_amount': self.currency_id.round(abs(line.amount_currency))} for line in self.line_ids.filtered(
            lambda x: x.tax_group_id.id in [
                self.env.ref('l10n_cl.tax_group_ila').id, self.env.ref('l10n_cl.tax_group_retenciones').id])]

    def _l10n_cl_get_dte_barcode_xml(self):
        """
        This method create the "stamp" (timbre). Is the auto-contained information inside the pdf417 barcode, which
        consists of a reduced xml version of the invoice, containing: issuer, recipient, folio and the first line
        of the invoice, etc.
        :return: xml that goes embedded inside the pdf417 code
        """
        dd = self.env['ir.qweb']._render('l10n_cl_edi.dd_template', {
            'move': self,
            'format_vat': self._l10n_cl_format_vat,
            'float_repr': float_repr,
            'format_length': self._format_length,
            'format_uom': self._format_uom,
            'time_stamp': self._get_cl_current_strftime(),
            'caf': self.l10n_latam_document_type_id._get_caf_file(self.company_id.id, int(self.l10n_latam_document_number)),
            '__keep_empty_lines': True,
        })
        caf_file = self.l10n_latam_document_type_id._get_caf_file(self.company_id.id, int(self.l10n_latam_document_number))
        ted = self.env['ir.qweb']._render('l10n_cl_edi.ted_template', {
            'dd': dd,
            'frmt': self._sign_message(dd.encode('ISO-8859-1', 'replace'), caf_file.findtext('RSASK')),
            'stamp': self._get_cl_current_strftime(),
            '__keep_empty_lines': True,
        })
        return {
            'ted': Markup(re.sub(r'\n\s*$', '', ted, flags=re.MULTILINE)),
            'barcode': etree.tostring(etree.fromstring(re.sub(
                r'<TmstFirma>.*</TmstFirma>', '', ted), parser=etree.XMLParser(remove_blank_text=True)))
        }

    def _l10n_cl_get_reverse_doc_type(self):
        if self.partner_id.l10n_cl_sii_taxpayer_type == '4' or self.partner_id.country_id.code != "CL":
            return self.env['l10n_latam.document.type'].search(
                [('code', '=', '112'), ('country_id.code', '=', "CL")], limit=1)
        return self.env['l10n_latam.document.type'].search(
            [('code', '=', '61'), ('country_id.code', '=', "CL")], limit=1)

    def _l10n_cl_get_comuna_recep(self):
        if self.partner_id._l10n_cl_is_foreign():
            return self._format_length(
                self.partner_id.state_id.name or self.commercial_partner_id.state_id.name or 'N-A', 20)
        if self.l10n_latam_document_type_id._is_doc_type_voucher():
            return 'N-A'
        return self.partner_id.city or self.commercial_partner_id.city or False

    def _l10n_cl_get_set_dte_id(self, xml_content):
        set_dte = xml_content.find('.//ns0:SetDTE', namespaces={'ns0': 'http://www.sii.cl/SiiDte'})
        set_dte_attrb = set_dte and set_dte.attrib or {}
        return set_dte_attrb.get('ID', '')

    # Cron methods

    def _l10n_cl_ask_dte_status(self):
        for move in self.search([('l10n_cl_dte_status', '=', 'ask_for_status')]):
            move.l10n_cl_verify_dte_status(send_dte_to_partner=False)
            self.env.cr.commit()

    def _l10n_cl_send_dte_to_partner_multi(self):
        for move in self.search([('l10n_cl_dte_status', '=', 'accepted'),
                                 ('l10n_cl_dte_partner_status', '=', 'not_sent'),
                                 ('partner_id.country_id.code', '=', "CL")]):
            _logger.debug('Sending %s DTE to partner' % move.name)
            if move.partner_id._l10n_cl_is_foreign():
                # review this option: if in the email will the pdf be included, the email should be sent
                # to foreign partners also
                continue
            move._l10n_cl_send_dte_to_partner()
            self.env.cr.commit()

    def _l10n_cl_ask_claim_status(self):
        for move in self.search([('l10n_cl_dte_acceptation_status', 'in', ['accepted', 'claimed']),
                                 ('move_type', 'in', ['out_invoice', 'out_refund']),
                                 ('l10n_cl_claim', '=', False)]):
            if move.company_id.l10n_cl_dte_service_provider == 'SIITEST':
                continue
            move.l10n_cl_verify_claim_status()
            self.env.cr.commit()

    def _pdf417_barcode(self, barcode_data):
        #  This method creates the graphic representation of the barcode
        barcode_file = BytesIO()
        if pdf417gen is None:
            return False
        bc = pdf417gen.encode(barcode_data, security_level=5, columns=13)
        image = pdf417gen.render_image(bc, padding=15, scale=1)
        image.save(barcode_file, 'PNG')
        data = barcode_file.getvalue()
        return base64.b64encode(data)

    # cron jobs
    def cron_run_sii_workflow(self):
        """
        This method groups all the steps needed to do the SII workflow:
        1.- Ask to SII for the status of the DTE sent
        2.- Send to the customer the DTE accepted by the SII
        3.- Ask the status of the DTE claimed by the customer
        """
        _logger.debug('Starting cron SII workflow')
        self_skip = self.with_context(cron_skip_connection_errs=True)
        self_skip._l10n_cl_ask_dte_status()
        self_skip._l10n_cl_send_dte_to_partner_multi()
        self_skip._l10n_cl_ask_claim_status()

    def cron_send_dte_to_sii(self):
        for record in self.search([('l10n_cl_dte_status', '=', 'not_sent')]):
            record.with_context(cron_skip_connection_errs=True).l10n_cl_send_dte_to_sii()
            self.env.cr.commit()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_cl_get_line_amounts(self):
        """
        This method is used to calculate the amount and taxes of the lines required in the Chilean localization
        electronic documents.
        """
        values = {
            'price_item': float(
                self.price_total / self.quantity) if self.move_id.l10n_latam_document_type_id._is_doc_type_voucher(
                ) and not self.l10n_latam_document_type_id._is_doc_type_electronic_ticket() else self.price_unit,
            'total_discount': '{:.0f}'.format(self.price_unit * self.quantity * self.discount / 100.0),
        }
        if self.move_id.currency_id != self.move_id.company_id.currency_id:
            rate = (self.move_id.currency_id + self.move_id.company_id.currency_id)._get_rates(
                self.move_id.company_id, self.move_id.date).get(self.move_id.currency_id.id) or 1
            second_currency_values = {
                'price': self.price_unit if not self.move_id.l10n_latam_document_type_id._is_doc_type_export(
                    ) else '{:.4f}'.format(self.price_unit / rate),
                'conversion_rate': '{:.4f}'.format((self.currency_id + self.company_id.currency_id)._get_rates(
                    self.company_id, self.move_id.date).get(
                    self.currency_id.id)) if self.move_id.l10n_latam_document_type_id._is_doc_type_export(
                        ) else False,
                'total_amount': '{:.4f}'.format(
                    self.price_subtotal / rate) if self.move_id.l10n_latam_document_type_id._is_doc_type_export(
                        ) else False,
            }
            values.update({'second_currency': second_currency_values})
        return values
