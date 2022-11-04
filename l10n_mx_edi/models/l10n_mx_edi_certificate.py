# -*- coding: utf-8 -*-

import base64
import logging
import ssl
import subprocess
import tempfile
from datetime import datetime
from lxml import etree, objectify

_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
except ImportError:
    _logger.warning('OpenSSL library not found. If you plan to use l10n_mx_edi, please install the library from https://pypi.python.org/pypi/pyOpenSSL')

from pytz import timezone

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


KEY_TO_PEM_CMD = 'openssl pkcs8 -in %s -inform der -outform pem -out %s -passin file:%s'


def convert_key_cer_to_pem(key, password):
    # TODO compute it from a python way
    with tempfile.NamedTemporaryFile('wb', suffix='.key', prefix='edi.mx.tmp.') as key_file, \
            tempfile.NamedTemporaryFile('wb', suffix='.txt', prefix='edi.mx.tmp.') as pwd_file, \
            tempfile.NamedTemporaryFile('rb', suffix='.key', prefix='edi.mx.tmp.') as keypem_file:
        key_file.write(key)
        key_file.flush()
        pwd_file.write(password)
        pwd_file.flush()
        subprocess.call((KEY_TO_PEM_CMD % (key_file.name, keypem_file.name, pwd_file.name)).split())
        key_pem = keypem_file.read()
    return key_pem


def str_to_datetime(dt_str, tz=timezone('America/Mexico_City')):
    return tz.localize(fields.Datetime.from_string(dt_str))


class Certificate(models.Model):
    _name = 'l10n_mx_edi.certificate'
    _description = 'SAT Digital Sail'
    _order = "date_start desc, id desc"

    content = fields.Binary(
        string='Certificate',
        help='Certificate in der format',
        required=True,
        attachment=False,)
    key = fields.Binary(
        string='Certificate Key',
        help='Certificate Key in der format',
        required=True,
        attachment=False,)
    password = fields.Char(
        string='Certificate Password',
        help='Password for the Certificate Key',
        required=True,)
    serial_number = fields.Char(
        string='Serial number',
        help='The serial number to add to electronic documents',
        readonly=True,
        index=True)
    date_start = fields.Datetime(
        string='Available date',
        help='The date on which the certificate starts to be valid',
        readonly=True)
    date_end = fields.Datetime(
        string='Expiration date',
        help='The date on which the certificate expires',
        readonly=True)

    @tools.ormcache('content')
    def _get_pem_cer(self, content):
        '''Get the current content in PEM format
        '''
        self.ensure_one()
        return ssl.DER_cert_to_PEM_cert(base64.decodebytes(content)).encode('UTF-8')

    @tools.ormcache('key', 'password')
    def _get_pem_key(self, key, password):
        '''Get the current key in PEM format
        '''
        self.ensure_one()
        return convert_key_cer_to_pem(base64.decodebytes(key), password.encode('UTF-8'))

    def _get_data(self):
        '''Return the content (b64 encoded) and the certificate decrypted
        '''
        self.ensure_one()
        cer_pem = self._get_pem_cer(self.content)
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
        for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            cer_pem = cer_pem.replace(to_del.encode('UTF-8'), b'')
        return cer_pem, certificate

    def get_mx_current_datetime(self):
        '''Get the current datetime with the Mexican timezone.
        '''
        return fields.Datetime.context_timestamp(
            self.with_context(tz='America/Mexico_City'), fields.Datetime.now())

    def _get_valid_certificate(self):
        '''Search for a valid certificate that is available and not expired.
        '''
        mexican_dt = self.get_mx_current_datetime()
        for record in self:
            date_start = str_to_datetime(record.date_start)
            date_end = str_to_datetime(record.date_end)
            if date_start <= mexican_dt <= date_end:
                return record
        return None

    def _get_encrypted_cadena(self, cadena):
        '''Encrypt the cadena using the private key.
        '''
        self.ensure_one()
        key_pem = self._get_pem_key(self.key, self.password)
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, bytes(key_pem))
        encrypt = 'sha256WithRSAEncryption'
        cadena_crypted = crypto.sign(private_key, bytes(cadena.encode()), encrypt)
        return base64.b64encode(cadena_crypted)

    @api.model
    def _get_cadena_chain(self, xml_tree, xslt_path):
        """ Use the provided XSLT document to generate a pipe-delimited string
        :param xml_tree: the source lxml document
        :param xslt_path: Path to the XSLT document
        :return: string
        """
        cadena_transformer = etree.parse(tools.file_open(xslt_path))
        return str(etree.XSLT(cadena_transformer)(xml_tree))

    def _certify_and_stamp(self, xml_content_str, xslt_path, no_cert_attrib_name='NoCertificado'):
        """ Appends the Sello stamp, certificate, and serial number to CFDI documents
        :param xml_content_str: The XML document string to certify and stamp
        :param xslt_path: Path to the XSLT used to generate the cadena chain (pipe delimited string of important values)
        :param no_cert_attrib_name: string of the NoCertificado (default) attribute which can be replaced with noCertificado
        :return: A string of the XML with appended attributes: NoCertificado, Certificado, Sello
        """
        # TODO: improve functions _l10n_mx_edi_export_payment_cfdi & _l10n_mx_edi_export_invoice_cfdi in l10n_mx_edi/models/account_edi_format.py
        self.ensure_one()
        if not xml_content_str:
            return None
        tree = objectify.fromstring(xml_content_str)
        tree.attrib[no_cert_attrib_name] = self.serial_number
        tree.attrib['Certificado'] = self._get_data()[0]
        cadena_chain = self._get_cadena_chain(tree, xslt_path)
        sello = self._get_encrypted_cadena(cadena_chain)
        tree.attrib['Sello'] = sello
        return etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    @api.constrains('content', 'key', 'password')
    def _check_credentials(self):
        '''Check the validity of content/key/password and fill the fields
        with the certificate values.
        '''
        mexican_tz = timezone('America/Mexico_City')
        mexican_dt = self.get_mx_current_datetime()
        date_format = '%Y%m%d%H%M%SZ'
        for record in self:
            # Try to decrypt the certificate
            try:
                certificate = record._get_data()[1]
                before = mexican_tz.localize(
                    datetime.strptime(certificate.get_notBefore().decode("utf-8"), date_format))
                after = mexican_tz.localize(
                    datetime.strptime(certificate.get_notAfter().decode("utf-8"), date_format))
                serial_number = certificate.get_serial_number()
            except UserError as exc_orm:  # ;-)
                raise exc_orm
            except Exception as e:
                raise ValidationError(_('The certificate content is invalid %s.', e))
            # Assign extracted values from the certificate
            record.serial_number = ('%x' % serial_number)[1::2]
            record.date_start = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.date_end = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if mexican_dt > after:
                raise ValidationError(_('The certificate is expired since %s', record.date_end))
            # Check the pair key/password
            try:
                key_pem = self._get_pem_key(self.key, self.password)
                crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
            except Exception:
                raise ValidationError(_('The certificate key and/or password is/are invalid.'))

    @api.ondelete(at_uninstall=True)
    def _unlink_except_invoices(self):
        mx_edi = self.env.ref('l10n_mx_edi.edi_cfdi_3_3')
        if self.env['account.edi.document'].sudo().search([
            ('edi_format_id', '=', mx_edi.id),
            ('state', '=', 'sent'),
        ], limit=1):
            raise UserError(_(
                'You cannot remove a certificate if at least an invoice has been signed. '
                'Expired Certificates will not be used as Odoo uses the latest valid certificate. '
                'To not use it, you can unlink it from the current company certificates.'))
