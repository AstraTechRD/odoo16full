# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import zipfile
import io
from requests.exceptions import ConnectionError as ReqConnectionError, HTTPError, InvalidSchema, InvalidURL, ReadTimeout
from zeep.wsse.username import UsernameToken
from zeep import Client, Settings
from zeep.transports import Transport
from lxml import etree
from lxml import objectify
from copy import deepcopy

from odoo import models, api, _, _lt
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError
from odoo.tools import float_round, html_escape

DEFAULT_IAP_ENDPOINT = 'https://iap-pe-edi.odoo.com'
DEFAULT_IAP_TEST_ENDPOINT = 'https://l10n-pe-edi-proxy-demo.odoo.com'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # EDI: HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pe_edi_zip_edi_document(self, documents):
        buffer = io.BytesIO()
        zipfile_obj = zipfile.ZipFile(buffer, 'w')
        for filename, content in documents:
            zipfile_obj.writestr(filename, content, compress_type=zipfile.ZIP_DEFLATED)
        zipfile_obj.close()
        content = buffer.getvalue()
        buffer.close()
        return content

    @api.model
    def _l10n_pe_edi_unzip_edi_document(self, zip_str):
        """Unzip the first XML file of a zip file,
        or, if the zip file does not contain an XML file, unzip the first file.
        :param zip_str: zipfile in base64 bytes
        :returns: the contents of the first xml file (or first file)
        """
        buffer = io.BytesIO(zip_str)
        zipfile_obj = zipfile.ZipFile(buffer)
        # We need to select the first xml file of the zip file because SUNAT sometimes sends a CDR zip file
        # which has an empty folder named 'dummy' as the first file in the zip file.
        filenames = zipfile_obj.namelist()
        xml_filenames = [x for x in filenames if x.endswith(('.xml', '.XML'))]
        filename_to_decode = xml_filenames[0] if xml_filenames else filenames[0]
        content = zipfile_obj.read(filename_to_decode)
        buffer.close()
        return content

    @api.model
    def _l10n_pe_edi_unzip_all_edi_documents(self, zip_bytes):
        """Unzips all the files of a base64 zip_bytes and if contains a CDR XML, it will unzip
        that one first
        :param zip_bytes: Zipfile in base64 that contains the response and signed XML
        :returns: xml files in base64
        """
        with io.BytesIO(base64.b64decode(zip_bytes)) as buffer:
            zip_bytes = zipfile.ZipFile(buffer)
            result = []
            for content_name in zip_bytes.namelist():
                xml_bytes = zip_bytes.read(content_name)
                application_response = etree.fromstring(xml_bytes).xpath('//applicationResponse')
                # If application response is in the xml file, we are actually interested in the contents of it
                # (which is a zip in base64, which contains the file we are interested in)
                if not application_response:
                    result.append([content_name, base64.b64encode(xml_bytes)])
                else:
                    unzipped_cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(application_response[0].text))
                    result.append([content_name[2:], base64.b64encode(unzipped_cdr)])
        return result

    @api.model
    def _l10n_pe_edi_get_general_error_messages(self):
        return {
            'L10NPE02': _lt("The zip file is corrupted, please check that the zip we are reading is the one you need."),
            'L10NPE03': _lt("The XML inside of the zip file is corrupted or has been altered, please review the XML "
                            "inside of the XML we are reading."),
            'L10NPE07': _lt("Trying to send the invoice to the OSE the webservice returned a controlled error, please "
                            "try again later, the error is on their side not here."),
            'L10NPE08': _lt("Check your firewall parameters, it is not being possible to connect with server to sign "
                            "invoices."),
            'L10NPE10': _lt("The URL provided to connect to the OSE is wrong, please check your implementation."),
            'L10NPE11': _lt("The XML generated is not valid."),
            'L10NPE16': _lt("There was an error while establishing the connection to the server, try again and "
                            "if it fails check the URL in the parameter l10n_pe_edi.endpoint."),
            'L10NPE17': _lt("There are problems with the connection to the IAP server. "
                            "Please try again in a few minutes."),
            'L10NPE18': _lt("The URL provided for the IAP server is wrong, please go to  Settings --> System "
                            "Parameters and add the right URL to parameter l10n_pe_edi.endpoint."),
        }

    @api.model
    def _l10n_pe_edi_get_cdr_error_messages(self):
        """The codes from the response of the CDR  and the service we are consulting must be processed to find if the
        message is common, if it is, we will set a friendly message giving instructions on how to fix the
        error/warning."""
        return {
            '2800': _lt("The type of identity document used for the client is not valid. Review the type of document "
                        "used in the client and change it according to the case of the document to be created. For "
                        "invoices it's only valid to use RUC as identity document."),
            '2801': _lt("The VAT you use for the customer is a DNI type, to be a valid DNI it must be the exact length "
                        "of 8 digits."),
            '2315': _lt("The cancellation reason field should not be empty when canceling the invoice, you must return "
                        "this invoice to Draft, edit the document and enter a cancellation reason."),
            '3105': _lt("One or more lines of this document do not have taxes assigned, to solve this you must return "
                        "the document to the Draft state and place taxes on the lines that do not have them."),
            '4332': _lt("One or more products do not have the UNSPSC code configured, to avoid this warning you must "
                        "configure a code for this product. This warning does not invalidate the document."),
            '2017': _lt("For invoices, the customer's identity document must be RUC. Check that the client has a valid "
                        "RUC and the type of document is RUC."),
            '3206': _lt("The type of operation is not valid for the type of document you are trying to create. The "
                        "document must return to Draft state and change the type of operation."),
            '2022': _lt("The name of the Partner must contain at least 2 characters and must not contain special characters."),
            '151': _lt("The name of the file depends on the sequence in the journal, please go to the journal and "
                       "configure the shortcode as LLL- (three (3) letters plus a dash and the 3 letters must be UPPERCASE.)"),
            '156': _lt("The zip file is corrupted, check again if the file trying to access is not damaged."),
            '2119': _lt("The invoice related to this Credit Note has not been reported, go to the invoice related and "
                        "sign it in order to generate this Credit Note."),
            '2120': _lt("The invoice related to this Credit Note has been canceled, set this document to draft and "
                        "cancel it."),
            '2209': _lt("The invoice related to this Debit Note has not been reported, go to the invoice related and "
                        "sign it in order to generate this Debit Note"),
            '2207': _lt("The invoice related to this Debit Note has been canceled, set this document to draft and "
                        "cancel it."),
            '001': _lt("This invoice has been validated by the OSE and we can not allow set it to draft, please try "
                       "to revert it with a credit not or cancel it and create a new one instead."),
            '1033': _lt("This document already exists on the OSE side.  Check if you gave a proper unique name to your "
                        "document. "),
            '1034': _lt("Check that the VAT set in the company is correct, this error generally happen when you did "
                        "not set a proper VAT in the company, go to company form and set it properly.."),
            '2371': _lt("Check your tax configuration, go to Configuration -> Taxes and set the field "
                        "'Affectation reason' to set it by default or set the proper value in the field Affect. Reason "
                        "in the line"),
            '2204': _lt("The document type of the invoice related is not the same of this document. Check the "
                        "document type of the invoice related and set this document with that document type. In case of "
                        "this document being posted and having a number already, reset to draft and cancel it, this "
                        "document will be cancelled locally and not reported."),
            '2116': _lt("The document type of the invoice related is not the same of this document. Check the "
                        "document type of the invoice related and set this document with that document type. In case of "
                        "this document being posted and having a number already, reset to draft and cancel it, this "
                        "document will be cancelled locally and not reported."),
            '3034': _lt("You need to configure the account for 'Banco de la Nación'. go to the Other Info setting"
                        " on this invoice and select the Recipient Bank field, If you want to set it by default go to "
                        "the partner related to your company and set the bank account related to the Banco de la "
                        "Nación"),
            '3128': _lt("As you have a document that must be detracted (withheld) which mean a document over 700 "
                        "Soles With services you must select on the 'Operation Type field the correct code 1001 "
                        "for example"),
            '154': _lt("Your RUC is not linked to Digiflow as OSE, please make sure you have follow this process in the SUNAT portal:\n"
                       "1. Linked Digiflow as OSE.\n"
                       "2. Authorize Digiflow as PSE.\n"
                       "Reference: \n"
                       "https://www.odoo.com/documentation/master/applications/finance/accounting/fiscal_localizations/localizations/peru.html#what-do-you-need-to-do"),
            '98': _lt("The cancellation request has not yet finished processing by SUNAT. Please retry in a few minutes.")
        }

    @api.model
    def _l10n_pe_edi_response_code_digiflow(self, cdr_tree):
        """
        Digiflow (our OSE)+IAP vs SUNAT have different responses, for digiflow:
        Example part of xml from Digiflow.-
        <s:Body>
            <s:Fault>
            <faultcode>s:Client</faultcode>
            <faultstring xml:lang="es-PE">2800</faultstring>
            <detail>
                <message xmlns="http://service.sunat.gob.pe">El dato ingresado en el tipo de documento de identidad del receptor no esta permitido. - Detalle: xxx.xxx.xxx ticket : 20210000000000070486326 error: Error Factura (codigo: 2800): 2800 (nodo: "cbc:ID/schemeID" valor: "7")</message>
            </detail>
            </s:Fault>
        </s:Body>
        """
        message_element = cdr_tree.find('.//{*}message')
        code_element = cdr_tree.find('.//{*}faultcode')
        code = False
        if code_element is not None: # faultcode is only when it is errored
            code = cdr_tree.find('.//{*}faultstring').text
        return message_element, code

    @api.model
    def _l10n_pe_edi_response_code_sunat(self, cdr_tree):
        """
        Digiflow (our OSE)+IAP vs SUNAT have different responses
        Example part of xml from SUNAT:
        <soap-env:Body>
            <soap-env:Fault xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <faultcode>soap-env:Client.2800</faultcode>
            <faultstring>El dato ingresado en el tipo de documento de identidad del receptor no esta permitido. - Detalle: xxx.xxx.xxx value=\'ticket: 1623742208882 error: INFO : 2800 (nodo: "cbc:ID/schemeID" valor: "7")\'</faultstring>
            </soap-env:Fault>
        </soap-env:Body>
        """
        message_element = cdr_tree.find('.//{*}faultstring')
        code_element = cdr_tree.find('.//{*}faultcode')
        code = False
        if code_element is not None: # faultcode is only when it is errored
            code_parsed = code_element.text.split('.')
            if len(code_parsed) == 2:  # Coming from SUNAT: "soap-env:Client.2800"
                code = code_parsed[1]
        return message_element, code

    def _l10n_pe_edi_decode_soap_response(self, soap_response):
        """
        Parse the SOAP response returned by any of the endpoints (IAP, Digiflow or SUNAT)
        for any of the SOAP operations (sendBill, getStatus, sendSummary, getStatusCdr),
        and extract, if they exist, the error, the response code, the CDR, etc.

        Returns a dict which can contain the following fields:
        'error': Description of the error (string with HTML format), if the response was a SOAP fault.
        'code': Response code (a string), if one was provided.
        'message': Description of the response status (a string), if one was provided.
        'number': Ticket number (a string) returned by the getSummary endpoint.
        'cdr': the CDR (bytes with XML format), if it was provided.
        """
        response_tree = etree.fromstring(soap_response)
        if response_tree.find('.//{*}Fault') is not None:
            if response_tree.find('.//{*}message') is not None:  # It comes from Digiflow
                message_element, code = self._l10n_pe_edi_response_code_digiflow(response_tree)
            else:  # It comes from SUNAT
                message_element, code = self._l10n_pe_edi_response_code_sunat(response_tree)
            message = message_element.text
            error_messages_map = self._l10n_pe_edi_get_cdr_error_messages()
            error_message = '%s<br/><br/><b>%s</b><br/>%s|%s' % (
                error_messages_map.get(code, _("We got an error response from the OSE. ")),
                _('Original message:'),
                html_escape(code),
                html_escape(message),
            )
            return {'error': error_message, 'code': code, 'message': message}
        if response_tree.find('.//{*}sendBillResponse') is not None:
            cdr_b64 = response_tree.find('.//{*}applicationResponse').text
            cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
            return {'cdr': cdr}
        if response_tree.find('.//{*}getStatusResponse') is not None:
            code = response_tree.find('.//{*}statusCode').text
            if response_tree.find('.//{*}content') is not None:
                cdr_b64 = response_tree.find('.//{*}content').text
                cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
            else:
                cdr = None
            return {'code': code, 'cdr': cdr}
        if response_tree.find('.//{*}sendSummaryResponse') is not None:
            ticket = response_tree.find('.//{*}ticket').text
            return {'number': ticket}
        if response_tree.find('.//{*}getStatusCdrResponse') is not None:
            cdr_b64 = response_tree.find('.//{*}content').text
            cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
            code = response_tree.find('.//{*}statusCode').text
            message = response_tree.find('.//{*}statusMessage').text
            return {'code': code, 'message': message, 'cdr': cdr}
        return {}

    _l10n_pe_edi_decode_cdr = _l10n_pe_edi_decode_soap_response

    def _l10n_pe_edi_extract_cdr_status(self, cdr):
        """
        Parse a CDR in XML format.

        Returns a dict that contains the following fields:
        'code': the ResponseCode of the CDR. 0 = success. Any other value = error.
        'description': a description of the CDR's response in HTML format, combining the
                       'Description' tag and the 'Note' tags.
        """
        cdr_tree = etree.fromstring(cdr)
        code = cdr_tree.find('.//{*}ResponseCode').text
        description = html_escape(cdr_tree.find('.//{*}Description').text)
        notes = cdr_tree.findall('.//{*}Note')
        for note in notes:
            description += '<br/>' + html_escape(note.text)

        if code != '0':
            error_messages_map = self._l10n_pe_edi_get_cdr_error_messages()
            description = '%s<br/><br/><b>%s</b><br/>%s|%s' % (
                error_messages_map.get(code, _("We got an error response from the OSE. ")),
                _('Original message:'),
                html_escape(code),
                html_escape(description),
            )

        return {'code': code, 'description': description}

    def _l10n_pe_edi_get_edi_values(self, invoice):
        self.ensure_one()
        price_precision = self.env['decimal.precision'].precision_get('Product Price')

        def format_float(amount, precision=2):
            ''' Helper to format monetary amount as a string with 2 decimal places. '''
            if amount is None or amount is False:
                return None
            return '%.*f' % (precision, amount)

        spot = invoice._l10n_pe_edi_get_spot()
        invoice_date_due_vals_list = []
        first_time = True
        for rec_line in invoice.line_ids.filtered(lambda l: l.account_type == 'asset_receivable'):
            amount = rec_line.amount_currency
            if spot and first_time:
                amount -= spot['spot_amount']
            first_time = False
            invoice_date_due_vals_list.append({'amount': rec_line.move_id.currency_id.round(amount),
                                               'currency_name': rec_line.move_id.currency_id.name,
                                               'date_maturity': rec_line.date_maturity})
        spot = invoice._l10n_pe_edi_get_spot()
        if not spot:
            total_after_spot = abs(invoice.amount_total)
        else:
            total_after_spot = abs(invoice.amount_total) - spot['spot_amount']
        values = {
            **invoice._prepare_edi_vals_to_export(),
            'spot': spot,
            'total_after_spot': total_after_spot,
            'PaymentMeansID': invoice._l10n_pe_edi_get_payment_means(),
            'is_refund': invoice.move_type in ('out_refund', 'in_refund'),
            'certificate_date': invoice.invoice_date,
            'price_precision': price_precision,
            'format_float': format_float,
            'invoice_date_due_vals_list': invoice_date_due_vals_list,
        }

        # Invoice lines.
        for line_vals in values['invoice_line_vals_list']:
            line = line_vals['line']
            line_vals['price_unit_type_code'] = '01' if not line.currency_id.is_zero(line_vals['price_unit_after_discount']) else '02'
            line_vals['price_subtotal_unit'] = float_round(line.price_subtotal / line.quantity, precision_digits=price_precision) if line.quantity else 0.0
            line_vals['price_total_unit'] = float_round(line.price_total / line.quantity, precision_digits=price_precision) if line.quantity else 0.0

        # Tax details.
        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            return {
                'l10n_pe_edi_code': tax.tax_group_id.l10n_pe_edi_code,
                'l10n_pe_edi_international_code': tax.l10n_pe_edi_international_code,
                'l10n_pe_edi_tax_code': tax.l10n_pe_edi_tax_code,
            }

        values['tax_details'] = invoice._prepare_edi_tax_details()
        values['tax_details_grouped'] = invoice._prepare_edi_tax_details(grouping_key_generator=grouping_key_generator)

        return values

    # -------------------------------------------------------------------------
    # EDI: IAP service
    # -------------------------------------------------------------------------

    def _l10n_pe_edi_get_iap_buy_credits_message(self, company):
        base_url = 'https://iap-sandbox.odoo.com/iap/1/credit' if company.l10n_pe_edi_test_env else ''
        url = self.env['iap.account'].get_credits_url(service_name="l10n_pe_edi", base_url=base_url)
        return '''<p><b>%s</b></p><p>%s</p>''' % (
            _('You have insufficient credits to sign or verify this document!'),
            _('Please proceed to buy more credits <a href="%s">here.</a>', html_escape(url)),
        )

    def _l10n_pe_edi_get_iap_params(self, company):
        ir_params = self.env['ir.config_parameter'].sudo()
        if company.l10n_pe_edi_test_env:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_ENDPOINT
        iap_server_url = ir_params.get_param('l10n_pe_edi.endpoint', default_endpoint)
        iap_token = self.env['iap.account'].get('l10n_pe_edi').account_token
        dbuuid = ir_params.get_param('database.uuid')
        return dbuuid, iap_server_url, iap_token

    def _l10n_pe_edi_sign_invoices_iap(self, invoice, edi_filename, edi_str):
        self.ensure_one()

        service_iap = self._l10n_pe_edi_sign_service_iap(
            invoice.company_id, edi_filename, edi_str, invoice.l10n_latam_document_type_id.code,
            invoice._l10n_pe_edi_get_serie_folio())
        if service_iap.get('extra_msg'):
            invoice.message_post(body=service_iap['extra_msg'])
        return service_iap

    def _l10n_pe_edi_sign_service_iap(self, company, edi_filename, edi_str, latam_document_type, serie_folio):
        edi_tree = objectify.fromstring(edi_str)

        # Dummy Signature to allow check the XSD, this will be replaced on IAP.
        namespaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
        edi_tree_copy = deepcopy(edi_tree)
        signature_element = edi_tree_copy.xpath('.//ds:Signature', namespaces=namespaces)[0]
        signature_str = self.env['ir.qweb']._render('l10n_pe_edi.pe_ubl_2_1_signature', {'digest_value': ''})
        signature_element.getparent().replace(signature_element, objectify.fromstring(signature_str))

        error = self.env['ir.attachment']._l10n_pe_edi_check_with_xsd(edi_tree_copy, latam_document_type)
        if error:
            return {'error': "<b>%s</b><br/>%s" % (_('XSD validation failed:'), html_escape(error)), 'blocking_level': 'error'}

        dbuuid, iap_server_url, iap_token = self._l10n_pe_edi_get_iap_params(company)

        rpc_params = {
            'vat': company.vat,
            'doc_type': latam_document_type,
            'dbuuid': dbuuid,
            'fname': edi_filename,
            'xml': base64.b64encode(edi_str).decode(),
            'token': iap_token,
        }

        try:
            result = iap_jsonrpc(iap_server_url + '/iap/l10n_pe_edi/1/send_bill', params=rpc_params, timeout=1500)
        except InvalidSchema:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE16'], 'blocking_level': 'error'}
        except AccessError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE17'], 'blocking_level': 'warning'}
        except InvalidURL:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE18'], 'blocking_level': 'error'}

        if result.get('message'):
            if result['message'] == 'no-credit':
                error_message = self._l10n_pe_edi_get_iap_buy_credits_message(company)
            else:
                error_message = result['message']
            return {'error': error_message, 'blocking_level': 'error'}

        soap_response = result.get('cdr') and base64.b64decode(result['cdr'])
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

        cdr = None
        extra_msg = ''
        if soap_response_decoded.get('error'):
            # Error code 1033 means that the invoice was already registered with the OSE.
            if soap_response_decoded.get('code') == '1033':
                status_cdr_response = self._l10n_pe_edi_get_status_cdr_iap_service(company, serie_folio, latam_document_type)
                if status_cdr_response.get('error'):
                    error_msg = '%s<br/>%s<br/>%s' % (soap_response_decoded['error'], _('Error requesting CDR status:'),
                                                      status_cdr_response['error'])
                    return {'error': error_msg, 'blocking_level': 'error'}
                # Status code 0004 means the CDR already exists.
                elif status_cdr_response.get('code') == '0004':
                    extra_msg = _('The invoice already exists on SUNAT. CDR successfully retrieved.')
                    cdr = status_cdr_response['cdr']
                else:
                    error_msg = '%s<br/>%s<br/>%s' % (soap_response_decoded['error'], _('CDR status:'), status_cdr_response['status'])
                    return {'error': error_msg, 'blocking_level': 'error'}
            else:
                return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        if not cdr:  # The 'cdr' variable might be set if we retrieved the cdr after getting error code 1033 - see above
            cdr = soap_response_decoded['cdr']

        cdr_status = self._l10n_pe_edi_extract_cdr_status(cdr)

        if cdr_status['code'] != '0':
            error_message = '%s<br/><br/><b>%s</b>' % (
                cdr_status['description'],
                _('This invoice number is now registered by SUNAT as invalid. Duplicate this invoice or create a new invoice to retry.')
            )
            return {'error': error_message, 'blocking_level': 'error'}

        xml_document = result.get('signed') and self._l10n_pe_edi_unzip_edi_document(base64.b64decode(result['signed']))
        return {'success': True, 'xml_document': xml_document, 'cdr': cdr, 'extra_msg': extra_msg}

    def _l10n_pe_edi_get_status_cdr_iap(self, invoice):
        self.ensure_one()
        return self._l10n_pe_edi_get_status_cdr_iap_service(
            invoice.company_id, invoice._l10n_pe_edi_get_serie_folio(), invoice.l10n_latam_document_type_id.code)

    def _l10n_pe_edi_get_status_cdr_iap_service(self, company, serie_folio, latam_document_type):
        dbuuid, iap_server_url, iap_token = self._l10n_pe_edi_get_iap_params(company)

        rpc_params = {
            'vat': company.vat,
            'doc_type': latam_document_type,
            'dbuuid': dbuuid,
            'serie': serie_folio['serie'],
            'folio': serie_folio['folio'],
            'token': iap_token,
        }

        try:
            result = iap_jsonrpc(iap_server_url + '/iap/l10n_pe_edi/1/get_status_cdr', params=rpc_params, timeout=1500)
        except InvalidSchema:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE16'], 'blocking_level': 'error'}
        except AccessError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE17'], 'blocking_level': 'warning'}
        except InvalidURL:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE18'], 'blocking_level': 'error'}

        if result.get('message'):
            if result['message'] == 'no-credit':
                error_message = self._l10n_pe_edi_get_iap_buy_credits_message(company)
            else:
                error_message = result['message']
            return {'error': error_message, 'blocking_level': 'error'}

        soap_response = result.get('cdr') and base64.b64decode(result['cdr'])
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

        if soap_response_decoded.get('error'):
            return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        code = soap_response_decoded.get('code')
        status = '%s|%s' % (html_escape(code), html_escape(soap_response_decoded.get('message')))
        cdr = soap_response_decoded.get('cdr')

        return {'cdr': cdr, 'status': status, 'code': code}

    def _l10n_pe_edi_cancel_invoices_step_1_iap(self, company, invoices, void_filename, void_str):
        self.ensure_one()
        dbuuid, iap_server_url, iap_token = self._l10n_pe_edi_get_iap_params(company)

        rpc_params = {
            'vat': company.vat,
            'dbuuid': dbuuid,
            'fname': void_filename,
            'xml': base64.encodebytes(void_str).decode('utf-8'),
            'token': iap_token,
        }

        try:
            result = iap_jsonrpc(iap_server_url + '/iap/l10n_pe_edi/1/send_summary', params=rpc_params, timeout=15)
        except AccessError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE17'], 'blocking_level': 'warning'}
        except KeyError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE18'], 'blocking_level': 'error'}

        if result.get('message'):
            if result['message'] == 'no-credit':
                error_message = self._l10n_pe_edi_get_iap_buy_credits_message(company)
            else:
                error_message = result['message']
            return {'error': error_message, 'blocking_level': 'error'}

        soap_response = result.get('cdr') and base64.b64decode(result['cdr'])
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

        if soap_response_decoded.get('error'):
            return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        cdr_number = soap_response_decoded['number']
        xml_document = result.get('signed') and self._l10n_pe_edi_unzip_edi_document(base64.b64decode(result['signed']))
        return {'xml_document': xml_document, 'cdr': soap_response, 'cdr_number': cdr_number}

    def _l10n_pe_edi_cancel_invoices_step_2_iap(self, company, edi_values, cdr_number):
        self.ensure_one()
        dbuuid, iap_server_url, iap_token = self._l10n_pe_edi_get_iap_params(company)

        rpc_params = {
            'vat': company.vat,
            'dbuuid': dbuuid,
            'number': cdr_number,
            'token': iap_token,
        }

        try:
            result = iap_jsonrpc(iap_server_url + '/iap/l10n_pe_edi/1/get_status', params=rpc_params, timeout=15)
        except KeyError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE18'], 'blocking_level': 'error'}
        except AccessError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE17'], 'blocking_level': 'warning'}

        if result.get('message'):
            if result['message'] == 'no-credit':
                error_message = self._l10n_pe_edi_get_iap_buy_credits_message(company)
            else:
                error_message = result['message']
            return {'error': error_message, 'blocking_level': 'error'}

        soap_response = result.get('cdr') and base64.b64decode(result['cdr'])
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

        if soap_response_decoded.get('error'):
            return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        if not soap_response_decoded.get('cdr'):
            # The server can respond with an error code 98 which means that the cancellation has
            # not yet finished processing. In this case, the response will not contain a CDR.
            # - see https://fe-primer.greenter.dev/docs/baja#envio-a-sunat
            code = soap_response_decoded.get('code')
            error_messages_map = self._l10n_pe_edi_get_cdr_error_messages()
            error_message = '%s<br/><br/><b>%s</b>%s' % (
                error_messages_map.get(code, _("We got an error response from the OSE. ")),
                _('Status code: '),
                html_escape(code),
            )
            return {'error': error_message, 'blocking_level': 'info'}

        cdr = soap_response_decoded['cdr']
        cdr_status = self._l10n_pe_edi_extract_cdr_status(cdr)

        if cdr_status['code'] != '0':
            return {'error': cdr_status['description'], 'blocking_level': 'error'}

        return {'success': True, 'cdr': cdr}

    # -------------------------------------------------------------------------
    # EDI: SUNAT / DIGIFLOW services
    # -------------------------------------------------------------------------

    def _l10n_pe_edi_post_invoice_web_service(self, invoice, edi_filename, edi_str):
        provider = invoice.company_id.l10n_pe_edi_provider
        res = getattr(self, '_l10n_pe_edi_sign_invoices_%s' % provider)(invoice, edi_filename, edi_str)

        if res.get('error'):
            return res

        # Chatter.
        documents = []
        if res.get('xml_document'):
            documents.append(('%s.xml' % edi_filename, res['xml_document']))
        if res.get('cdr'):
            documents.append(('CDR-%s.xml' % edi_filename, res['cdr']))
        if documents:
            zip_edi_str = self._l10n_pe_edi_zip_edi_document(documents)
            res['attachment'] = self.env['ir.attachment'].create({
                'res_model': invoice._name,
                'res_id': invoice.id,
                'type': 'binary',
                'name': '%s.zip' % edi_filename,
                'datas': base64.encodebytes(zip_edi_str),
                'mimetype': 'application/zip',
            })
            message = _("The EDI document was successfully created and signed by the government.")
            invoice.with_context(no_new_invoice=True).message_post(
                body=message,
                attachment_ids=res['attachment'].ids,
            )

        return res

    def _l10n_pe_edi_get_digiflow_credentials(self, company):
        self.ensure_one()
        res = {'fault_ns': 's'}
        if company.l10n_pe_edi_test_env:
            res.update({
                'wsdl': 'https://ose-test.com/ol-ti-itcpe/',
                'token': UsernameToken('20557912879MODDATOS', 'moddatos'),
            })
        else:
            res.update({
                'wsdl': 'https://ose.pe/ol-ti-itcpe/billService',
                'token': UsernameToken(company.l10n_pe_edi_provider_username, company.l10n_pe_edi_provider_password),
            })
        return res

    def _l10n_pe_edi_get_sunat_credentials(self, company):
        self.ensure_one()
        res = {'fault_ns': 'soap-env'}
        if company.l10n_pe_edi_test_env:
            res.update({
                'wsdl': 'https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl',
                'token': UsernameToken('MODDATOS', 'MODDATOS'),
            })
        else:
            res.update({
                'wsdl': self._get_sunat_wsdl(),
                'token': UsernameToken(company.l10n_pe_edi_provider_username, company.l10n_pe_edi_provider_password),
            })
        return res

    def _l10n_pe_edi_sign_invoices_sunat_digiflow_common(self, invoice, edi_filename, edi_str, credentials):
        return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
            invoice.company_id, edi_filename, edi_str, credentials, invoice.l10n_latam_document_type_id.code)

    def _l10n_pe_edi_sign_service_sunat_digiflow_common(self, company, edi_filename, edi_str, credentials, latam_document_type):
        if not company.l10n_pe_edi_certificate_id:
            return {'error': _("No valid certificate found for %s company.", company.display_name)}

        # Sign the document.
        edi_tree = objectify.fromstring(edi_str)
        edi_tree = company.l10n_pe_edi_certificate_id.sudo()._sign(edi_tree)
        error = self.env['ir.attachment']._l10n_pe_edi_check_with_xsd(edi_tree, latam_document_type)
        if error:
            return {'error': _('XSD validation failed: %s', error), 'blocking_level': 'error'}
        edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding='ISO-8859-1')

        zip_edi_str = self._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
        transport = Transport(operation_timeout=15, timeout=15)
        try:
            settings = Settings(raw_response=True)
            client = Client(
                wsdl=credentials['wsdl'],
                wsse=credentials['token'],
                settings=settings,
                transport=transport,
            )
            result = client.service.sendBill('%s.zip' % edi_filename, zip_edi_str)
            result.raise_for_status()
        except ReqConnectionError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE08'], 'blocking_level': 'warning'}
        except HTTPError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE10'], 'blocking_level': 'warning'}
        except TypeError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE11'], 'blocking_level': 'error'}
        except ReadTimeout:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE12'], 'blocking_level': 'warning'}
        soap_response = result.content
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

        if soap_response_decoded.get('error'):
            return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        cdr = soap_response_decoded['cdr']
        cdr_status = self._l10n_pe_edi_extract_cdr_status(cdr)

        if cdr_status['code'] != '0':
            error_message = '%s<br/><br/><b>%s</b>' % (
                cdr_status['description'],
                _('This invoice number is now registered by SUNAT as invalid. Duplicate this invoice or create a new invoice to retry.')
            )
            return {'error': error_message, 'blocking_level': 'error'}

        return {'success': True, 'xml_document': edi_str, 'cdr': cdr}

    def _l10n_pe_edi_sign_invoices_sunat(self, invoice, edi_filename, edi_str):
        """This method calls _l10n_pe_edi_sign_service_sunat() to allow inherit this second from other models"""
        return self._l10n_pe_edi_sign_service_sunat(invoice.company_id, edi_filename, edi_str, invoice.l10n_latam_document_type_id.code)

    def _l10n_pe_edi_sign_service_sunat(self, company, edi_filename, edi_str, latam_document_type, serie=False):
        credentials = self._l10n_pe_edi_get_sunat_credentials(company)
        return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
            company, edi_filename, edi_str, credentials, latam_document_type)

    def _l10n_pe_edi_sign_invoices_digiflow(self, invoice, edi_filename, edi_str):
        # TODO: To be refactored in master
        return self._l10n_pe_edi_sign_service_digiflow(invoice.company_id, edi_filename, edi_str, invoice.l10n_latam_document_type_id.code)

    def _l10n_pe_edi_sign_service_digiflow(self, company, edi_filename, edi_str, latam_document_type, serie=False):
        credentials = self._l10n_pe_edi_get_digiflow_credentials(company)
        return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
            company, edi_filename, edi_str, credentials, latam_document_type)

    def _l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(self, company, invoices, void_filename, void_str, credentials):
        self.ensure_one()

        void_tree = objectify.fromstring(void_str)
        void_tree = company.l10n_pe_edi_certificate_id.sudo()._sign(void_tree)
        void_str = etree.tostring(void_tree, xml_declaration=True, encoding='ISO-8859-1')
        zip_void_str = self._l10n_pe_edi_zip_edi_document([('%s.xml' % void_filename, void_str)])
        transport = Transport(operation_timeout=15, timeout=15)

        try:
            settings = Settings(raw_response=True)
            client = Client(
                wsdl=credentials['wsdl'],
                wsse=credentials['token'],
                settings=settings,
                transport=transport,
            )
            result = client.service.sendSummary('%s.zip' % void_filename,  zip_void_str)
            result.raise_for_status()
        except (InvalidSchema, KeyError):
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE08'], 'blocking_level': 'error'}

        soap_response = result.content
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response)

        if soap_response_decoded.get('error'):
            return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        cdr_number = soap_response_decoded['number']
        return {'xml_document': void_str, 'cdr': soap_response, 'cdr_number': cdr_number}

    def _l10n_pe_edi_cancel_invoices_step_1_sunat(self, company, invoices, void_filename, void_str):
        credentials = self._l10n_pe_edi_get_sunat_credentials(company)
        return self._l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(company, invoices, void_filename, void_str, credentials)

    def _l10n_pe_edi_cancel_invoices_step_1_digiflow(self, company, invoices, void_filename, void_str):
        credentials = self._l10n_pe_edi_get_digiflow_credentials(company)
        return self._l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(company, invoices, void_filename, void_str, credentials)

    def _l10n_pe_edi_cancel_invoices_step_2_sunat_digiflow_common(self, company, edi_values, cdr_number, credentials):
        self.ensure_one()

        transport = Transport(operation_timeout=15, timeout=15)

        try:
            settings = Settings(raw_response=True)
            client = Client(
                wsdl=credentials['wsdl'],
                wsse=credentials['token'],
                settings=settings,
                transport=transport,
            )
            result = client.service.getStatus(cdr_number)
            result.raise_for_status()
        except (InvalidSchema, KeyError):
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE08'], 'blocking_level': 'error'}

        soap_response = result.content
        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response)

        if soap_response_decoded.get('error'):
            return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

        if not soap_response_decoded.get('cdr'):
            # The server can respond with an error code 98 which means that the cancellation has
            # not yet finished processing. In this case, the response will not contain a CDR.
            # - see https://fe-primer.greenter.dev/docs/baja#envio-a-sunat
            code = soap_response_decoded.get('code')
            error_messages_map = self._l10n_pe_edi_get_cdr_error_messages()
            error_message = '%s<br/><br/><b>%s</b>%s' % (
                error_messages_map.get(code, _("We got an error response from the OSE. ")),
                _('Status code: '),
                html_escape(code),
            )
            return {'error': error_message, 'blocking_level': 'info'}

        cdr = soap_response_decoded['cdr']
        cdr_status = self._l10n_pe_edi_extract_cdr_status(cdr)

        if cdr_status['code'] != '0':
            return {'error': cdr_status['description'], 'blocking_level': 'error'}

        return {'success': True, 'cdr': cdr}

    def _l10n_pe_edi_cancel_invoices_step_2_sunat(self, company, edi_values, cdr_number):
        credentials = self._l10n_pe_edi_get_sunat_credentials(company)
        return self._l10n_pe_edi_cancel_invoices_step_2_sunat_digiflow_common(company, edi_values, cdr_number, credentials)

    def _l10n_pe_edi_cancel_invoices_step_2_digiflow(self, company, edi_values, cdr_number):
        credentials = self._l10n_pe_edi_get_digiflow_credentials(company)
        return self._l10n_pe_edi_cancel_invoices_step_2_sunat_digiflow_common(company, edi_values, cdr_number, credentials)

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'pe_ubl_2_1':
            return super()._get_move_applicability(move)

        if move.l10n_pe_edi_is_required:
            return {
                'post': self._l10n_pe_edi_sign_invoice,
                'cancel': self._l10n_pe_edi_cancel_invoices,
                'cancel_batching': lambda invoice: (invoice.l10n_pe_edi_cancel_cdr_number,),
                'edi_content': self._l10n_pe_edi_xml_invoice_content,
            }

    def _l10n_pe_edi_xml_invoice_content(self, invoice):
        return self._generate_edi_invoice_bstr(invoice)

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == 'pe_ubl_2_1' or super()._needs_web_services()

    def _check_move_configuration(self, move):
        # OVERRIDE
        res = super()._check_move_configuration(move)
        if self.code != 'pe_ubl_2_1':
            return res

        if not move.company_id.vat:
            res.append(_("VAT number is missing on company %s") % move.company_id.display_name)
        if not move.commercial_partner_id.vat:
            res.append(_("VAT number is missing on partner %s") % move.commercial_partner_id.display_name)
        lines = move.invoice_line_ids.filtered(lambda line: not line.display_type)
        for line in lines:
            taxes = line.tax_ids
            if len(taxes) > 1 and len(taxes.filtered(lambda t: t.tax_group_id.l10n_pe_edi_code == 'IGV')) > 1:
                res.append(_("You can't have more than one IGV tax per line to generate a legal invoice in Peru"))
        if any(not line.tax_ids for line in move.invoice_line_ids if not line.display_type):
            res.append(_("Taxes need to be assigned on all invoice lines"))

        return res

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        if self.code != 'pe_ubl_2_1':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'PE' and journal.l10n_latam_use_documents

    def _generate_edi_invoice_bstr(self, invoice):
        latam_invoice_type = self._get_latam_invoice_type(invoice.l10n_latam_document_type_id.code)
        if not latam_invoice_type:
            return _("Missing LATAM document code.").encode()
        edi_values = self._l10n_pe_edi_get_edi_values(invoice)
        return self.env['ir.qweb']._render('l10n_pe_edi.%s' % latam_invoice_type, edi_values)

    def _get_latam_invoice_type(self, code):
        template_by_latam_type_mapping = {
            '07': 'pe_ubl_2_1_credit_note',
            '08': 'pe_ubl_2_1_debit_note',
            '01': 'pe_ubl_2_1_invoice',
            '03': 'pe_ubl_2_1_invoice',
        }
        return template_by_latam_type_mapping.get(code, False)

    def _l10n_pe_edi_sign_invoice(self, invoice):
        edi_filename = '%s-%s-%s' % (
            invoice.company_id.vat,
            invoice.l10n_latam_document_type_id.code,
            invoice.name.replace(' ', ''),
        )
        latam_invoice_type = self._get_latam_invoice_type(invoice.l10n_latam_document_type_id.code)

        if not latam_invoice_type:
            return {invoice: {'error': _("Missing LATAM document code.")}}

        edi_values = self._l10n_pe_edi_get_edi_values(invoice)
        edi_str = self.env['ir.qweb']._render('l10n_pe_edi.%s' % latam_invoice_type, edi_values).encode()

        res = self._l10n_pe_edi_post_invoice_web_service(invoice, edi_filename, edi_str)

        return {invoice: res}

    def _l10n_pe_edi_cancel_invoice_edi_step_1(self, invoices):
        self.ensure_one()
        certificate_date = self.env['l10n_pe_edi.certificate']._get_pe_current_datetime().date()
        reference_date = invoices[0].invoice_date
        company = invoices[0].company_id # documents are always batched by company in account_edi.
        provider = company.l10n_pe_edi_provider

        # Prepare the void documents to void all invoices at once.
        void_number = self.env['ir.sequence'].next_by_code('l10n_pe_edi.summary.sequence')
        void_values = {
            'certificate_date': certificate_date,
            'reference_date': reference_date,
            'void_number': void_number,
            'company': company,
            'records': invoices,
        }
        void_str = self.env['ir.qweb']._render('l10n_pe_edi.pe_ubl_2_1_void_documents', void_values).encode()
        void_filename = '%s-%s' % (company.vat, void_number)

        res = getattr(self, '_l10n_pe_edi_cancel_invoices_step_1_%s' % provider)(company, invoices, void_filename, void_str)

        if res.get('error'):
            return {invoice: res for invoice in invoices}

        if not res.get('cdr_number'):
            error = _("The EDI document failed to be cancelled because the cancellation CDR number is missing.")
            return {invoice: {'error': error} for invoice in invoices}

        # Chatter.
        message = _("Cancellation is in progress in the government side (CDR number: %s).", html_escape(res['cdr_number']))
        if res.get('xml_document'):
            void_attachment = self.env['ir.attachment'].create({
                'type': 'binary',
                'name': 'VOID-%s.xml' % void_filename,
                'datas': base64.encodebytes(res['xml_document']),
                'mimetype': 'application/xml',
            })
            for invoice in invoices:
                invoice.with_context(no_new_invoice=True).message_post(
                    body=message,
                    attachment_ids=void_attachment.ids,
                )

        invoices.write({'l10n_pe_edi_cancel_cdr_number': res['cdr_number']})
        return {invoice: {'error': message, 'blocking_level': 'info'} for invoice in invoices}

    def _l10n_pe_edi_cancel_invoice_edi_step_2(self, invoices, edi_attachments, cdr_number):
        self.ensure_one()
        company = invoices[0].company_id # documents are always batched by company in account_edi.
        provider = company.l10n_pe_edi_provider
        edi_values = list(zip(invoices, edi_attachments))

        res = getattr(self, '_l10n_pe_edi_cancel_invoices_step_2_%s' % provider)(company, edi_values, cdr_number)

        if res.get('error'):
            return {invoice: res for invoice in invoices}
        if not res.get('success'):
            error = _("The EDI document failed to be cancelled for unknown reason.")
            return {invoice: {'error': error} for invoice in invoices}

        # Chatter.
        message = _("The EDI document was successfully cancelled by the government (CDR number: %s).", html_escape(cdr_number))
        for invoice, attachment in edi_values:
            cdr_void_attachment = self.env['ir.attachment'].create({
                'res_model': invoice._name,
                'res_id': invoice.id,
                'type': 'binary',
                'name': 'CDR-VOID-%s.xml' % attachment.name[:-4],
                'datas': base64.encodebytes(res['cdr']),
                'mimetype': 'application/xml',
            })
            invoice.with_context(no_new_invoice=True).message_post(
                body=message,
                attachment_ids=cdr_void_attachment.ids,
            )
        invoices.write({'l10n_pe_edi_cancel_cdr_number': False})
        return {invoice: {'success': True} for invoice in invoices}

    def _l10n_pe_edi_cancel_invoices(self, invoices):
        # OVERRIDE
        if self.code != 'pe_ubl_2_1':
            return super()._cancel_invoice_edi(invoices)

        company = invoices[0].company_id # documents are always batched by company in account_edi.
        edi_attachments = self.env['ir.attachment']
        res = {}
        for invoice in invoices:

            if not invoice.l10n_pe_edi_cancel_reason:
                res[invoice] = {'error': _("Please put a cancel reason")}
                continue

            edi_attachments |= invoice._get_edi_attachment(self)

        res = {}
        invoices_with_cdr = invoices.filtered('l10n_pe_edi_cancel_cdr_number')
        if invoices_with_cdr:
            # Cancel part 2.
            # Ensure the whole batch of invoices sharing the same number is there. Return an error if it's not the case
            # because the whole batch must be processed at once and locked in order to avoid asynchronous errors.
            cdr_number = invoices_with_cdr[0].l10n_pe_edi_cancel_cdr_number
            invoices_same_number = invoices_with_cdr.filtered(lambda move: move.l10n_pe_edi_cancel_cdr_number == cdr_number)
            all_invoices_same_number = self.env['account.move'].search([
                ('l10n_pe_edi_cancel_cdr_number', '=', cdr_number),
                ('company_id', '=', company.id),
            ])
            if len(invoices_same_number) == len(all_invoices_same_number):
                # Process.
                edi_attachments = self.env['ir.attachment']
                for invoice in invoices_same_number:
                    edi_attachments |= invoice._get_edi_attachment(self)
                res.update(self._l10n_pe_edi_cancel_invoice_edi_step_2(invoices_same_number, edi_attachments, cdr_number))
            else:
                # Error.
                for invoice in invoices_same_number:
                    res[invoice] = {'error': _("All invoices sharing the same CDR number (%s) must be processed at once", html_escape(cdr_number))}
        else:
            # Cancel part 1.
            res.update(self._l10n_pe_edi_cancel_invoice_edi_step_1(invoices))

        return res

    def _get_sunat_wsdl(self):
        """This method will handle the SUNAT WSDL, in production we have an error while using zeep because of one
        definition that has no binding, so, we just store the XML of the service and remove the unvalid data.
        Reported https://github.com/mvantellingen/python-zeep/issues/924
        """
        return io.BytesIO(b'''
            <wsdl:definitions xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/" xmlns:soap11="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:soap12="http://schemas.xmlsoap.org/wsdl/soap12/" xmlns:http="http://schemas.xmlsoap.org/wsdl/http/" xmlns:mime="http://schemas.xmlsoap.org/wsdl/mime/" xmlns:wsp="http://www.w3.org/ns/ws-policy" xmlns:wsp200409="http://schemas.xmlsoap.org/ws/2004/09/policy" xmlns:wsp200607="http://www.w3.org/2006/07/ws-policy" xmlns:ns0="http://service.gem.factura.comppago.registro.servicio.sunat.gob.pe/" xmlns:ns1="http://service.sunat.gob.pe" xmlns:ns2="http://www.datapower.com/extensions/http://schemas.xmlsoap.org/wsdl/soap12/" targetNamespace="http://service.gem.factura.comppago.registro.servicio.sunat.gob.pe/">
            <wsdl:import location="https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService?ns1.wsdl" namespace="http://service.sunat.gob.pe"/>
            <wsdl:binding name="BillServicePortBinding" type="ns1:billService">
                <soap11:binding transport="http://schemas.xmlsoap.org/soap/http" style="document"/>
                <wsdl:operation name="getStatus">
                <soap11:operation soapAction="urn:getStatus" style="document"/>
                <wsdl:input name="getStatusRequest">
                    <soap11:body use="literal"/>
                </wsdl:input>
                <wsdl:output name="getStatusResponse">
                    <soap11:body use="literal"/>
                </wsdl:output>
                </wsdl:operation>
                <wsdl:operation name="sendBill">
                <soap11:operation soapAction="urn:sendBill" style="document"/>
                <wsdl:input name="sendBillRequest">
                    <soap11:body use="literal"/>
                </wsdl:input>
                <wsdl:output name="sendBillResponse">
                    <soap11:body use="literal"/>
                </wsdl:output>
                </wsdl:operation>
                <wsdl:operation name="sendPack">
                <soap11:operation soapAction="urn:sendPack" style="document"/>
                <wsdl:input name="sendPackRequest">
                    <soap11:body use="literal"/>
                </wsdl:input>
                <wsdl:output name="sendPackResponse">
                    <soap11:body use="literal"/>
                </wsdl:output>
                </wsdl:operation>
                <wsdl:operation name="sendSummary">
                <soap11:operation soapAction="urn:sendSummary" style="document"/>
                <wsdl:input name="sendSummaryRequest">
                    <soap11:body use="literal"/>
                </wsdl:input>
                <wsdl:output name="sendSummaryResponse">
                    <soap11:body use="literal"/>
                </wsdl:output>
                </wsdl:operation>
            </wsdl:binding>
            <wsdl:service name="billService">
                <wsdl:port name="BillServicePort" binding="ns0:BillServicePortBinding">
                <soap11:address location="https://e-factura.sunat.gob.pe:443/ol-ti-itcpfegem/billService"/>
                </wsdl:port>
                <wsdl:port name="BillServicePort.0" binding="ns2:BillServicePortBinding">
                <soap12:address location="https://e-factura.sunat.gob.pe:443/ol-ti-itcpfegem/billService"/>
                </wsdl:port>
                <wsdl:port name="BillServicePort.3" binding="ns0:BillServicePortBinding">
                <soap11:address location="https://e-factura.sunat.gob.pe:443/ol-ti-itcpfegem/billService"/>
                </wsdl:port>
            </wsdl:service>
            </wsdl:definitions>''')
