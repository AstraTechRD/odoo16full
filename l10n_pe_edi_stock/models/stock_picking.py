# -*- coding: utf-8 -*-

import base64
import logging
import re
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ATTACHMENT_NAME = 'Sunat_DeliveryGuide_{}.xml'
DEFAULT_PE_DATE_FORMAT = '%Y-%m-%d'
PE_TRANSFER_REASONS = [
    ('01', 'Sale'),
    ('04', 'Transfer between establishments of the same company'),
    ('13', 'Others'),
    ('14', "Sale subject to buyer's confirmation"),
    ('18', 'Transfer issuer itinerant cp'),
    ('19', 'Transfer to primary zone'),
]


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_pe_edi_transport_type = fields.Selection(
        selection=[
            ('01', 'Public transport'),
            ('02', 'Private transport'),
        ], copy=False)
    l10n_pe_edi_status = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
        ],
        string='Delivery Guide Status (PE)',
        copy=False)
    country_code = fields.Char(
        related='company_id.country_id.code',
        depends=['company_id.country_id'])
    l10n_pe_edi_error = fields.Html(
        copy=False)
    l10n_pe_edi_reason_for_transfer = fields.Selection(
        selection=PE_TRANSFER_REASONS,
        string='Reason for transfer',
        # Used compute method instead of a default to only set the value if the transport type is set
        compute='_compute_l10n_pe_edi_reason_for_transfer',
        store=True,
        readonly=False)
    l10n_pe_edi_departure_start_date = fields.Date(
        'Transfer Start Date',
        help='By default this is when the transfer is validated, but to make it possible to '
        'still send the delivery guide when the transport is some days later, the user can still adapt this date.')
    l10n_pe_edi_vehicle_id = fields.Many2one(
        comodel_name='l10n_pe_edi.vehicle',
        copy=False,
        check_company=True)
    l10n_pe_edi_operator_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_l10n_pe_edi_operator',
        store=True,
        readonly=False,
        check_company=True,
        help='If the transport is public, please define the transport provider, else, the internal operator.')
    l10n_latam_document_number = fields.Char(
        string='Delivery Guide Number',
        copy=False)
    l10n_pe_edi_observation = fields.Text(
        'Observation',
        help='Additional information to be displayed in the Delivery Slip in order to clarify or '
        'complement information about the transferred products. It has a maximum length of 250 characters.')
    l10n_pe_edi_content = fields.Binary(
        compute='_l10n_pe_edi_compute_edi_content',
        compute_sudo=True)

    def _l10n_pe_edi_compute_edi_content(self):
        for picking in self:
            picking.l10n_pe_edi_content = base64.b64encode(picking._l10n_pe_edi_create_delivery_guide())

    def l10n_pe_edi_action_clear_error(self):
        for record in self:
            record.l10n_pe_edi_error = False

    def l10n_pe_edi_action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/stock.picking/%s/l10n_pe_edi_content' % self.id
        }

    @api.depends('l10n_pe_edi_vehicle_id')
    def _compute_l10n_pe_edi_operator(self):
        for record in self:
            record.l10n_pe_edi_operator_id = record.l10n_pe_edi_vehicle_id.operator_id or record.l10n_pe_edi_operator_id

    @api.depends('l10n_pe_edi_transport_type')
    def _compute_l10n_pe_edi_reason_for_transfer(self):
        """ We use a compute to avoid setting 01 where the delivery guide is not applied """
        for record in self:
            record.l10n_pe_edi_reason_for_transfer = record.l10n_pe_edi_reason_for_transfer or '01'

    # Validation

    def _l10n_pe_edi_check_required_data(self):
        """Some attributes are required to allow generate the XML file, that attributes are review here to avoid SUNAT
        errors."""
        for record in self:
            errors = []
            pac_name = record.company_id.l10n_pe_edi_provider
            # certificate only required on Sunat And Digiflow
            if record.company_id.country_id.code != 'PE' or (
                    pac_name in ('digiflow', 'sunat') and not record.company_id.l10n_pe_edi_certificate_id):
                errors.append(_("This company has no connection with the Sunat configured."))
            if not record.partner_id:
                errors.append(_('Please set a Delivery Address as the delivery guide needs one.'))
            if not record.partner_id.l10n_pe_district:
                errors.append(_('The client must have a defined district.'))
            if not record.l10n_pe_edi_transport_type:
                errors.append(_('You must select a transport type to generate the delivery guide.'))
            if not record.l10n_pe_edi_reason_for_transfer:
                errors.append(_('You must choose the reason for the transfer.'))
            if not record.l10n_pe_edi_departure_start_date:
                errors.append(_('You must choose the start date of the transfer.'))
            if record.l10n_pe_edi_transport_type == '02' and not record.l10n_pe_edi_vehicle_id:
                errors.append(_('You must choose the transfer vehicle.'))
            if record.l10n_pe_edi_transport_type == '02' and not record.l10n_pe_edi_operator_id:
                errors.append(_('You must choose the transfer operator.'))
            if not record.company_id.partner_id.l10n_latam_identification_type_id:
                errors.append(_('A document type is required for the company.'))
            if not record.company_id.partner_id.vat:
                errors.append(_('An identification number is required for the company.'))
            warehouse_address = record.picking_type_id.warehouse_id.partner_id or record.company_id.partner_id
            if not warehouse_address.l10n_pe_district:
                errors.append(_('The origin address must have a defined district.'))
            if not warehouse_address.street:
                errors.append(_('The origin address must have a defined street.'))
            if not errors:
                continue
            raise UserError(_("Invalid picking configuration:\n\n%s") % '\n'.join(errors))

    def button_validate(self):
        picking = super().button_validate()
        self.l10n_pe_edi_departure_start_date = fields.Datetime.now()
        return picking

    def _l10n_pe_edi_create_delivery_guide(self):
        """ Used to generate the XML file that will be send to stamp in SUNAT
        The document number comes from the sequence with code "l10n_pe_edi_stock.stock_picking_sunat_sequence", and
        will be generated automatically if this not exists."""
        self.ensure_one()

        def format_date(date):
            return date.strftime(DEFAULT_PE_DATE_FORMAT) if date else ''

        def format_float(val, digits=2):
            return '%.*f' % (digits, val)

        if not self.l10n_latam_document_number:
            sunat_sequence = self.env['ir.sequence'].search([
                ('code', '=', 'l10n_pe_edi_stock.stock_picking_sunat_sequence'),
                ('company_id', '=', self.company_id.id)], limit=1)
            if not sunat_sequence:
                sunat_sequence = self.env['ir.sequence'].sudo().create({
                    'name': 'Stock Picking Sunat Sequence %s' % self.company_id.name,
                    'code': 'l10n_pe_edi_stock.stock_picking_sunat_sequence',
                    'padding': 8,
                    'company_id': self.company_id.id,
                    'prefix': 'T001-',
                    'number_next': 1,
                })
            self.l10n_latam_document_number = sunat_sequence.next_by_id()
        self.l10n_pe_edi_status = 'to_send'
        date_pe = self.env['l10n_pe_edi.certificate']._get_pe_current_datetime().date()
        values = {
            'date_issue': date_pe.strftime(DEFAULT_PE_DATE_FORMAT),
            'time_issue': date_pe.strftime("%H:%M:%S"),
            'l10n_pe_edi_observation': self.l10n_pe_edi_observation or 'Guía',
            'record': self,
            'weight_uom': self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(),
            'warehouse_address': self.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id,
            'document_number': self.l10n_latam_document_number,
            'format_date': format_date,
            'moves': self.move_ids.filtered(lambda ml: ml.quantity_done > 0),
            'reason_for_transfer': dict(PE_TRANSFER_REASONS)[self.l10n_pe_edi_reason_for_transfer],
            'format_float': format_float,

        }
        xml = self.env['ir.qweb']._render('l10n_pe_edi_stock.sunat_guiaremision', values).encode()
        return xml

    def action_send_delivery_guide(self):
        """Make the validations required to generate the EDI document, generates the XML, and sent to sign in the
        SUNAT"""
        self._check_company()
        self._l10n_pe_edi_check_required_data()
        pe_edi_format = self.env.ref('l10n_pe_edi.edi_pe_ubl_2_1')
        for record in self:
            pac_name = record.company_id.l10n_pe_edi_provider
            edi_str = record._l10n_pe_edi_create_delivery_guide()

            edi_filename = '%s-09-%s' % (
                self.company_id.vat,
                self.l10n_latam_document_number.replace(' ', ''),
            )

            res = getattr(pe_edi_format, '_l10n_pe_edi_sign_service_%s' % pac_name)(
                self.company_id, edi_filename, edi_str, '09', self._l10n_pe_edi_get_serie_folio())

            if res.get('error'):
                record.l10n_pe_edi_error = res['error']
                continue

            # == Create the attachment ==
            documents = []
            if res.get('xml_document'):
                documents.append(('%s.xml' % edi_filename, res['xml_document']))
                record._l10n_pe_edi_decode_cdr(edi_filename, res['xml_document'])
            if res.get('cdr'):
                documents.append(('cdr-%s.xml' % edi_filename, res['cdr']))
            if documents:
                zip_edi_str = pe_edi_format._l10n_pe_edi_zip_edi_document(documents)
                res_attachment = self.env['ir.attachment'].create({
                    'res_model': record._name,
                    'res_id': record.id,
                    'type': 'binary',
                    'name': '%s.zip' % edi_filename,
                    'datas': base64.encodebytes(zip_edi_str),
                    'mimetype': 'application/zip',
                })
            message = _("The EDI document was successfully created and signed by the government.")
            record._message_log(body=message, attachment_ids=res_attachment.ids)
            record.write({'l10n_pe_edi_error': False, 'l10n_pe_edi_status': 'sent'})

    def _l10n_pe_edi_decode_cdr(self, edi_filename, xml_document):
        self.ensure_one()
        res_attachment = self.env['ir.attachment'].create({
            'name': edi_filename + '.xml',
            'res_id': self.id,
            'res_model': self._name,
            'type': 'binary',
            'raw': xml_document,
            'mimetype': 'application/xml',
            'description': _('Decode Delivery Guide sunat generated for the %s document.', self.name),
        })
        message = _("The Sunat document Delivery Guide decode")
        self._message_log(body=message, attachment_ids=res_attachment.ids)

    def _l10n_pe_edi_get_serie_folio(self):
        number_match = [rn for rn in re.finditer(r'\d+', self.l10n_latam_document_number.replace(' ', ''))]
        serie = self.name[:number_match[-1].start()].replace('-', '').replace(' ', '') or None
        folio = number_match[-1].group() or None
        return {'serie': serie, 'folio': folio}
