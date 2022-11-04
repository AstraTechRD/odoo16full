# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_repr

import base64
import requests

from lxml import etree
from lxml.objectify import fromstring
from pytz import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

CFDI_XSLT_CADENA = 'l10n_mx_edi/data/3.3/cadenaoriginal.xslt'
CFDI_XSLT_CADENA_TFD = 'l10n_mx_edi/data/xslt/3.3/cadenaoriginal_TFD_1_1.xslt'


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ==== CFDI flow fields ====
    l10n_mx_edi_cfdi_request = fields.Selection(
        selection=[
            ('on_invoice', "On Invoice"),
            ('on_refund', "On Credit Note"),
            ('on_payment', "On Payment"),
        ],
        string="Request a CFDI", store=True,
        compute='_compute_l10n_mx_edi_cfdi_request',
        help="Flag indicating a CFDI should be generated for this journal entry.")
    l10n_mx_edi_sat_status = fields.Selection(
        selection=[
            ('none', "State not defined"),
            ('undefined', "Not Synced Yet"),
            ('not_found', "Not Found"),
            ('cancelled', "Cancelled"),
            ('valid', "Valid"),
        ],
        string="SAT status", readonly=True, copy=False, required=True, tracking=True,
        default='undefined',
        help="Refers to the status of the journal entry inside the SAT system.")
    l10n_mx_edi_post_time = fields.Datetime(
        string="Posted Time", readonly=True, copy=False,
        help="Keep empty to use the current México central time")
    l10n_mx_edi_usage = fields.Selection(
        selection=[
            ('G01', 'Acquisition of merchandise'),
            ('G02', 'Returns, discounts or bonuses'),
            ('G03', 'General expenses'),
            ('I01', 'Constructions'),
            ('I02', 'Office furniture and equipment investment'),
            ('I03', 'Transportation equipment'),
            ('I04', 'Computer equipment and accessories'),
            ('I05', 'Dices, dies, molds, matrices and tooling'),
            ('I06', 'Telephone communications'),
            ('I07', 'Satellite communications'),
            ('I08', 'Other machinery and equipment'),
            ('D01', 'Medical, dental and hospital expenses.'),
            ('D02', 'Medical expenses for disability'),
            ('D03', 'Funeral expenses'),
            ('D04', 'Donations'),
            ('D05', 'Real interest effectively paid for mortgage loans (room house)'),
            ('D06', 'Voluntary contributions to SAR'),
            ('D07', 'Medical insurance premiums'),
            ('D08', 'Mandatory School Transportation Expenses'),
            ('D09', 'Deposits in savings accounts, premiums based on pension plans.'),
            ('D10', 'Payments for educational services (Colegiatura)'),
            ('P01', 'To define'),
        ],
        string="Usage",
        default='P01',
        help="Used in CFDI 3.3 to express the key to the usage that will gives the receiver to this invoice. This "
             "value is defined by the customer.\nNote: It is not cause for cancellation if the key set is not the usage "
             "that will give the receiver of the document.")
    l10n_mx_edi_origin = fields.Char(
        string='CFDI Origin',
        copy=False,
        help="In some cases like payments, credit notes, debit notes, invoices re-signed or invoices that are redone "
             "due to payment in advance will need this field filled, the format is:\n"
             "Origin Type|UUID1, UUID2, ...., UUIDn.\n"
             "Where the origin type could be:\n"
             "- 01: Nota de crédito\n"
             "- 02: Nota de débito de los documentos relacionados\n"
             "- 03: Devolución de mercancía sobre facturas o traslados previos\n"
             "- 04: Sustitución de los CFDI previos\n"
             "- 05: Traslados de mercancias facturados previamente\n"
             "- 06: Factura generada por los traslados previos\n"
             "- 07: CFDI por aplicación de anticipo")
    l10n_mx_edi_cancel_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Substituted By",
        compute='_compute_l10n_mx_edi_cancel',
        readonly=True)
    # ==== CFDI certificate fields ====
    l10n_mx_edi_certificate_id = fields.Many2one(
        comodel_name='l10n_mx_edi.certificate',
        string="Source Certificate")
    l10n_mx_edi_cer_source = fields.Char(
        string='Certificate Source',
        help="Used in CFDI like attribute derived from the exception of certificates of Origin of the "
             "Free Trade Agreements that Mexico has celebrated with several countries. If it has a value, it will "
             "indicate that it serves as certificate of origin and this value will be set in the CFDI node "
             "'NumCertificadoOrigen'.")

    # ==== CFDI attachment fields ====
    l10n_mx_edi_cfdi_uuid = fields.Char(string='Fiscal Folio', copy=False, readonly=True, store=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_l10n_mx_edi_cfdi_uuid')
    l10n_mx_edi_cfdi_supplier_rfc = fields.Char(string='Supplier RFC', copy=False, readonly=True,
        help='The supplier tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_customer_rfc = fields.Char(string='Customer RFC', copy=False, readonly=True,
        help='The customer tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_amount = fields.Monetary(string='Total Amount', copy=False, readonly=True,
        help='The total amount reported on the cfdi.',
        compute='_compute_cfdi_values')

    # ==== Other fields ====
    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        compute='_compute_l10n_mx_edi_payment_method_id',
        store=True,
        readonly=False,
        help="Indicates the way the invoice was/will be paid, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc. Leave empty if unkown and the XML will show 'Unidentified'.")
    l10n_mx_edi_payment_policy = fields.Selection(string='Payment Policy',
        selection=[('PPD', 'PPD'), ('PUE', 'PUE')],
        compute='_compute_l10n_mx_edi_payment_policy')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_get_cadena_xslts(self):
        return CFDI_XSLT_CADENA_TFD, CFDI_XSLT_CADENA

    def _get_l10n_mx_edi_signed_edi_document(self):
        self.ensure_one()
        return self.edi_document_ids.filtered(lambda document: document.edi_format_id.code == 'cfdi_3_3' and document.attachment_id)

    def _get_l10n_mx_edi_issued_address(self):
        self.ensure_one()
        return self.company_id.partner_id.commercial_partner_id

    def _l10n_mx_edi_get_tax_objected(self):
        return '02'

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        ''' Helper to extract relevant data from the CFDI to be used, for example, when printing the invoice.
        :param cfdi_data:   The optional cfdi data.
        :return:            A python dictionary.
        '''
        self.ensure_one()

        def get_node(cfdi_node, attribute, namespaces):
            if hasattr(cfdi_node, 'Complemento'):
                node = cfdi_node.Complemento.xpath(attribute, namespaces=namespaces)
                return node[0] if node else None
            else:
                return None

        def get_cadena(cfdi_node, template):
            if cfdi_node is None:
                return None
            cadena_root = etree.parse(tools.file_open(template))
            return str(etree.XSLT(cadena_root)(cfdi_node))

        def is_purchase_move(move):
            return move.move_type in move.get_purchase_types() \
                    or move.payment_id.reconciled_bill_ids

        # Find a signed cfdi.
        if not cfdi_data:
            signed_edi = self._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)

            # For vendor bills, the CFDI XML must be posted in the chatter as an attachment.
            elif is_purchase_move(self) and self.country_code == 'MX' and not self.l10n_mx_edi_cfdi_request:
                attachments = self.attachment_ids.filtered(lambda x: x.mimetype == 'application/xml')
                if attachments:
                    attachment = sorted(attachments, key=lambda x: x.create_date)[-1]
                    cfdi_data = base64.decodebytes(attachment.with_context(bin_size=False).datas)

        # Nothing to decode.
        if not cfdi_data:
            return {}

        try:
            cfdi_node = fromstring(cfdi_data)
            emisor_node = cfdi_node.Emisor
            receptor_node = cfdi_node.Receptor
        except etree.XMLSyntaxError:
            # Not an xml
            return {}
        except AttributeError:
            # Not a CFDI
            return {}

        tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
        )

        return {
            'uuid': ({} if tfd_node is None else tfd_node).get('UUID'),
            'supplier_rfc': emisor_node.get('Rfc', emisor_node.get('rfc')),
            'customer_rfc': receptor_node.get('Rfc', receptor_node.get('rfc')),
            'amount_total': cfdi_node.get('Total', cfdi_node.get('total')),
            'cfdi_node': cfdi_node,
            'usage': receptor_node.get('UsoCFDI'),
            'payment_method': cfdi_node.get('formaDePago', cfdi_node.get('MetodoPago')),
            'bank_account': cfdi_node.get('NumCtaPago'),
            'sello': cfdi_node.get('sello', cfdi_node.get('Sello', 'No identificado')),
            'sello_sat': tfd_node is not None and tfd_node.get('selloSAT', tfd_node.get('SelloSAT', 'No identificado')),
            'cadena': tfd_node is not None and get_cadena(tfd_node, self._l10n_mx_edi_get_cadena_xslts()[0]) or get_cadena(cfdi_node, self._l10n_mx_edi_get_cadena_xslts()[1]),
            'certificate_number': cfdi_node.get('noCertificado', cfdi_node.get('NoCertificado')),
            'certificate_sat_number': tfd_node is not None and tfd_node.get('NoCertificadoSAT'),
            'expedition': cfdi_node.get('LugarExpedicion'),
            'fiscal_regime': emisor_node.get('RegimenFiscal', ''),
            'emission_date_str': cfdi_node.get('fecha', cfdi_node.get('Fecha', '')).replace('T', ' '),
            'stamp_date': tfd_node is not None and tfd_node.get('FechaTimbrado', '').replace('T', ' '),
        }

    @api.model
    def _l10n_mx_edi_cfdi_amount_to_text(self):
        """Method to transform a float amount to text words
        E.g. 100 - ONE HUNDRED
        :returns: Amount transformed to words mexican format for invoices
        :rtype: str
        """
        self.ensure_one()

        currency_name = self.currency_id.name.upper()

        # M.N. = Moneda Nacional (National Currency)
        # M.E. = Moneda Extranjera (Foreign Currency)
        currency_type = 'M.N' if currency_name == 'MXN' else 'M.E.'

        # Split integer and decimal part
        amount_i, amount_d = divmod(self.amount_total, 1)
        amount_d = round(amount_d, 2)
        amount_d = int(round(amount_d * 100, 2))

        words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(amount_i).upper()
        return '%(words)s %(amount_d)02d/100 %(currency_type)s' % {
            'words': words,
            'amount_d': amount_d,
            'currency_type': currency_type,
        }

    @api.model
    def _l10n_mx_edi_write_cfdi_origin(self, code, uuids):
        ''' Format the code and uuids passed as parameter in order to fill the l10n_mx_edi_origin field.
        The code corresponds to the following types:
            - 01: Nota de crédito
            - 02: Nota de débito de los documentos relacionados
            - 03: Devolución de mercancía sobre facturas o traslados previos
            - 04: Sustitución de los CFDI previos
            - 05: Traslados de mercancias facturados previamente
            - 06: Factura generada por los traslados previos
            - 07: CFDI por aplicación de anticipo

        The generated string must match the following template:
        <code>|<uuid1>,<uuid2>,...,<uuidn>

        :param code:    A valid code as a string between 01 and 07.
        :param uuids:   A list of uuids returned by the government.
        :return:        A valid string to be put inside the l10n_mx_edi_origin field.
        '''
        return '%s|%s' % (code, ','.join(uuids))

    @api.model
    def _l10n_mx_edi_read_cfdi_origin(self, cfdi_origin):
        splitted = cfdi_origin.split('|')
        if len(splitted) != 2:
            return False

        try:
            code = int(splitted[0])
        except ValueError:
            return False

        if code < 1 or code > 7:
            return False
        return splitted[0], [uuid.strip() for uuid in splitted[1].split(',')]

    @api.model
    def _l10n_mx_edi_get_cfdi_partner_timezone(self, partner):
        code = partner.state_id.code

        # northwest area
        if code == 'BCN':
            return timezone('America/Tijuana')
        # Southeast area
        elif code == 'ROO':
            return timezone('America/Cancun')
        # Pacific area
        elif code in ('BCS', 'CHH', 'SIN', 'NAY'):
            return timezone('America/Chihuahua')
        # Sonora
        elif code == 'SON':
            return timezone('America/Hermosillo')
        # By default, takes the central area timezone
        return timezone('America/Mexico_City')

    @api.model
    def _l10n_mx_edi_is_managing_invoice_negative_lines_allowed(self):
        """ Negative lines are not allowed by the Mexican government making some features unavailable like sale_coupon
        or global discounts. This method allows odoo to distribute the negative discount lines to each others making
        such features available even for Mexican people.

        :return: True if odoo needs to distribute the negative discount lines, False otherwise.
        """
        param_name = 'l10n_mx_edi.manage_invoice_negative_lines'
        return bool(self.env['ir.config_parameter'].sudo().get_param(param_name))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id', 'state')
    def _compute_l10n_mx_edi_cfdi_request(self):
        for move in self:
            if move.country_code != 'MX':
                move.l10n_mx_edi_cfdi_request = False
            elif move.move_type == 'out_invoice':
                move.l10n_mx_edi_cfdi_request = 'on_invoice'
            elif move.move_type == 'out_refund':
                move.l10n_mx_edi_cfdi_request = 'on_refund'
            elif (move.payment_id and move.payment_id.payment_type == 'inbound' and
                'PPD' in move._get_reconciled_invoices().mapped('l10n_mx_edi_payment_policy')):
                move.l10n_mx_edi_cfdi_request = 'on_payment'
            elif move.statement_line_id:
                move.l10n_mx_edi_cfdi_request = 'on_payment'
            else:
                move.l10n_mx_edi_cfdi_request = False

    @api.depends('edi_document_ids', 'edi_document_ids.state', 'attachment_ids')
    def _compute_l10n_mx_edi_cfdi_uuid(self):
        '''Fill the invoice fields from the cfdi values.
        '''
        for move in self:
            cfdi_infos = move._l10n_mx_edi_decode_cfdi()
            move.l10n_mx_edi_cfdi_uuid = cfdi_infos.get('uuid')

    @api.depends('edi_document_ids')
    def _compute_cfdi_values(self):
        '''Fill the invoice fields from the cfdi values.
        '''
        for move in self:
            cfdi_infos = move._l10n_mx_edi_decode_cfdi()
            move.l10n_mx_edi_cfdi_supplier_rfc = cfdi_infos.get('supplier_rfc')
            move.l10n_mx_edi_cfdi_customer_rfc = cfdi_infos.get('customer_rfc')
            move.l10n_mx_edi_cfdi_amount = cfdi_infos.get('amount_total')

    @api.depends('move_type', 'invoice_date_due', 'invoice_date', 'invoice_payment_term_id', 'invoice_payment_term_id.line_ids')
    def _compute_l10n_mx_edi_payment_policy(self):
        for move in self:
            if move.is_invoice(include_receipts=True) and move.invoice_date_due and move.invoice_date:
                if move.move_type == 'out_invoice':
                    # In CFDI 3.3 - rule 2.7.1.43 which establish that
                    # invoice payment term should be PPD as soon as the due date
                    # is after the last day of  the month (the month of the invoice date).
                    if move.invoice_date_due.month > move.invoice_date.month or \
                       move.invoice_date_due.year > move.invoice_date.year or \
                       len(move.invoice_payment_term_id.line_ids) > 1:  # to be able to force PPD
                        move.l10n_mx_edi_payment_policy = 'PPD'
                    else:
                        move.l10n_mx_edi_payment_policy = 'PUE'
                else:
                    move.l10n_mx_edi_payment_policy = 'PUE'
            else:
                move.l10n_mx_edi_payment_policy = False

    @api.depends('journal_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        for move in self:
            if move.l10n_mx_edi_payment_method_id:
                move.l10n_mx_edi_payment_method_id = move.l10n_mx_edi_payment_method_id
            elif move.journal_id.l10n_mx_edi_payment_method_id:
                move.l10n_mx_edi_payment_method_id = move.journal_id.l10n_mx_edi_payment_method_id
            else:
                move.l10n_mx_edi_payment_method_id = self.env.ref('l10n_mx_edi.payment_method_otros', raise_if_not_found=False)

    def _compute_l10n_mx_edi_cancel(self):
        for move in self:
            if move.l10n_mx_edi_cfdi_uuid:
                replaced_move = move.search(
                    [('l10n_mx_edi_origin', 'like', '04|%'),
                     ('l10n_mx_edi_origin', 'like', '%' + move.l10n_mx_edi_cfdi_uuid + '%'),
                     ('company_id', '=', move.company_id.id)],
                    limit=1,
                )
                move.l10n_mx_edi_cancel_move_id = replaced_move
            else:
                move.l10n_mx_edi_cancel_move_id = None

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('l10n_mx_edi_origin')
    def _check_l10n_mx_edi_origin(self):
        error_message = _("The following CFDI origin %s is invalid and must match the "
                          "<code>|<uuid1>,<uuid2>,...,<uuidn> template.\n"
                          "Here are the specification of this value:\n"
                          "- 01: Nota de crédito\n"
                          "- 02: Nota de débito de los documentos relacionados\n"
                          "- 03: Devolución de mercancía sobre facturas o traslados previos\n"
                          "- 04: Sustitución de los CFDI previos\n"
                          "- 05: Traslados de mercancias facturados previamente\n"
                          "- 06: Factura generada por los traslados previos\n"
                          "- 07: CFDI por aplicación de anticipo\n"
                          "For example: 01|89966ACC-0F5C-447D-AEF3-3EED22E711EE,89966ACC-0F5C-447D-AEF3-3EED22E711EE")

        for move in self:
            if not move.l10n_mx_edi_origin:
                continue

            # This method
            decoded_origin = move._l10n_mx_edi_read_cfdi_origin(move.l10n_mx_edi_origin)
            if not decoded_origin:
                raise ValidationError(error_message % move.l10n_mx_edi_origin)

    # -------------------------------------------------------------------------
    # SAT
    # -------------------------------------------------------------------------

    def l10n_mx_edi_update_sat_status(self):
        '''Synchronize both systems: Odoo & SAT to make sure the invoice is valid.
        '''
        for move in self:
            supplier_rfc = move.l10n_mx_edi_cfdi_supplier_rfc
            customer_rfc = move.l10n_mx_edi_cfdi_customer_rfc
            total = float_repr(move.l10n_mx_edi_cfdi_amount, precision_digits=move.currency_id.decimal_places)
            uuid = move.l10n_mx_edi_cfdi_uuid

            # If the CFDI attachment was unlinked from the edi_document (e.g. when canceling the invoice),
            # the l10n_mx_edi_cfdi_uuid, ... fields will have been set to False.
            # However, the attachment might still be there, so try to retrieve it.
            cfdi_doc = move.edi_document_ids.filtered(lambda document: document.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))
            if cfdi_doc and not cfdi_doc.attachment_id:
                attachment = self.env['ir.attachment'].search([('name', 'like', '%-MX-Invoice-3.3.xml'), ('res_model', '=', 'account.move'), ('res_id', '=', move.id)], limit=1, order='create_date desc')
                if attachment:
                    cfdi_data = base64.decodebytes(attachment.with_context(bin_size=False).datas)
                    cfdi_infos = move._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi_data)
                    uuid = cfdi_infos['uuid']
                    supplier_rfc = cfdi_infos['supplier_rfc']
                    customer_rfc = cfdi_infos['customer_rfc']
                    total = cfdi_infos['amount_total']

            try:
                status = self.env['account.edi.format']._l10n_mx_edi_get_sat_status(supplier_rfc, customer_rfc, total, uuid)
            except Exception as e:
                move.message_post(body=_("Failure during update of the SAT status: %(msg)s", msg=str(e)))
                continue

            if status == 'Vigente':
                move.l10n_mx_edi_sat_status = 'valid'
            elif status == 'Cancelado':
                move.l10n_mx_edi_sat_status = 'cancelled'
            elif status == 'No Encontrado':
                move.l10n_mx_edi_sat_status = 'not_found'
            else:
                move.l10n_mx_edi_sat_status = 'none'

    @api.model
    def _l10n_mx_edi_cron_update_sat_status(self):
        ''' Call the SAT to know if the invoice is available government-side or if the invoice has been cancelled.
        In the second case, the cancellation could be done Odoo-side and then we need to check if the SAT is up-to-date,
        or could be done manually government-side forcing Odoo to update the invoice's state.
        '''

        # Update the 'l10n_mx_edi_sat_status' field.
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3')
        to_process = self.env['account.edi.document'].search([
            ('edi_format_id', '=', cfdi_edi_format.id),
            ('state', 'in', ('sent', 'cancelled')),
            ('move_id.l10n_mx_edi_sat_status', 'in', ('undefined', 'not_found', 'none')),
        ])
        to_process.move_id.l10n_mx_edi_update_sat_status()

        # Handle the case when the invoice has been cancelled manually government-side.
        to_process\
            .filtered(lambda doc: doc.state == 'sent' and doc.move_id.l10n_mx_edi_sat_status == 'cancelled')\
            .move_id\
            .button_cancel()

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _update_payments_edi_documents(self):
        # OVERRIDE
        # Set the cfdi origin with code '04' meaning the payment becomes an update of its previous state.
        for payment in self:
            if payment.l10n_mx_edi_cfdi_uuid:
                payment.l10n_mx_edi_origin = payment._l10n_mx_edi_write_cfdi_origin('04', [payment.l10n_mx_edi_cfdi_uuid])
        return super()._update_payments_edi_documents()

    def _post(self, soft=True):
        # OVERRIDE
        certificate_date = self.env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime()

        for move in self:

            issued_address = move._get_l10n_mx_edi_issued_address()
            tz = self._l10n_mx_edi_get_cfdi_partner_timezone(issued_address)
            tz_force = self.env['ir.config_parameter'].sudo().get_param('l10n_mx_edi_tz_%s' % move.journal_id.id, default=None)
            if tz_force:
                tz = timezone(tz_force)

            move.l10n_mx_edi_post_time = fields.Datetime.to_string(datetime.now(tz))

            if move.l10n_mx_edi_cfdi_request in ('on_invoice', 'on_refund'):
                # Assign time and date coming from a certificate.
                if not move.invoice_date:
                    move.invoice_date = certificate_date.date()

        return super()._post(soft=soft)

    def button_draft(self):
        # OVERRIDE
        for move in self:
            if move.l10n_mx_edi_cfdi_uuid:
                move.l10n_mx_edi_origin = move._l10n_mx_edi_write_cfdi_origin('04', [move.l10n_mx_edi_cfdi_uuid])
            if move.payment_id:
                move.payment_id.l10n_mx_edi_force_generate_cfdi = False
            elif move.statement_line_id:
                move.statement_line_id.l10n_mx_edi_force_generate_cfdi = False

        return super().button_draft()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # OVERRIDE
        # The '01' code is used to indicate the document is a credit note.
        if not default_values_list:
            default_values_list = [{}] * len(self)

        for default_vals, move in zip(default_values_list, self):
            if move.l10n_mx_edi_cfdi_uuid:
                default_vals['l10n_mx_edi_origin'] = move._l10n_mx_edi_write_cfdi_origin('01', [move.l10n_mx_edi_cfdi_uuid])
        return super()._reverse_moves(default_values_list, cancel=cancel)

    @api.model
    def get_invoice_localisation_fields_required_to_invoice(self, country_id):
        res = super().get_invoice_localisation_fields_required_to_invoice(country_id)
        if country_id.code == 'MX':
            res.extend([self.env['ir.model.fields']._get(self._name, 'l10n_mx_edi_usage')])
        return res
