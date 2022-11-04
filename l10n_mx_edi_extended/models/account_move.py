# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.sql import column_exists, create_column

import re


CUSTOM_NUMBERS_PATTERN = re.compile(r'[0-9]{2}  [0-9]{2}  [0-9]{4}  [0-9]{7}')


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_external_trade = fields.Boolean(
        string="Need external trade?",
        readonly=False, store=True,
        compute='_compute_l10n_mx_edi_external_trade',
        help="If this field is active, the CFDI that generates this invoice will include the complement "
             "'External Trade'.")

    def _get_l10n_mx_edi_issued_address(self):
        # OVERRIDE
        self.ensure_one()
        return self.journal_id.l10n_mx_address_issued_id or super()._get_l10n_mx_edi_issued_address()

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        # OVERRIDE

        def get_node(cfdi_node, attribute, namespaces):
            if hasattr(cfdi_node, 'Complemento'):
                node = cfdi_node.Complemento.xpath(attribute, namespaces=namespaces)
                return node[0] if node else None
            else:
                return None

        vals = super()._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi_data)
        if vals.get('cfdi_node') is None:
            return vals

        cfdi_node = vals['cfdi_node']

        external_trade_node = get_node(
            cfdi_node,
            'cce11:ComercioExterior[1]',
            {'cce11': 'http://www.sat.gob.mx/ComercioExterior11'},
        )
        if external_trade_node is None:
            external_trade_node = {}

        vals.update({
            'ext_trade_node': external_trade_node,
            'ext_trade_certificate_key': external_trade_node.get('ClaveDePedimento', ''),
            'ext_trade_certificate_source': external_trade_node.get('CertificadoOrigen', '').replace('0', 'No').replace('1', 'Si'),
            'ext_trade_nb_certificate_origin': external_trade_node.get('CertificadoOrigen', ''),
            'ext_trade_certificate_origin': external_trade_node.get('NumCertificadoOrigen', ''),
            'ext_trade_operation_type': external_trade_node.get('TipoOperacion', '').replace('2', 'Exportación'),
            'ext_trade_subdivision': external_trade_node.get('Subdivision', ''),
            'ext_trade_nb_reliable_exporter': external_trade_node.get('NumeroExportadorConfiable', ''),
            'ext_trade_incoterm': external_trade_node.get('Incoterm', ''),
            'ext_trade_rate_usd': external_trade_node.get('TipoCambioUSD', ''),
            'ext_trade_total_usd': external_trade_node.get('TotalUSD', ''),
        })

        return vals

    @api.depends('partner_id')
    def _compute_l10n_mx_edi_external_trade(self):
        for move in self:
            if move.l10n_mx_edi_cfdi_request == 'on_invoice':
                move.l10n_mx_edi_external_trade = move.partner_id.l10n_mx_edi_external_trade
            else:
                move.l10n_mx_edi_external_trade = False


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "l10n_mx_edi_umt_aduana_id"):
            create_column(self.env.cr, "account_move_line", "l10n_mx_edi_umt_aduana_id", "int4")
            # Since l10n_mx_edi_umt_aduana_id columns does not exist we can assume the columns
            # l10n_mx_edi_qty_umt and l10n_mx_edi_price_unit_umt do not exist either
            create_column(self.env.cr, "account_move_line", "l10n_mx_edi_qty_umt", "numeric")
            create_column(self.env.cr, "account_move_line", "l10n_mx_edi_price_unit_umt", "float8")
        return super()._auto_init()

    l10n_mx_edi_customs_number = fields.Char(
        help='Optional field for entering the customs information in the case '
        'of first-hand sales of imported goods or in the case of foreign trade'
        ' operations with goods or services.\n'
        'The format must be:\n'
        ' - 2 digits of the year of validation followed by two spaces.\n'
        ' - 2 digits of customs clearance followed by two spaces.\n'
        ' - 4 digits of the serial number followed by two spaces.\n'
        ' - 1 digit corresponding to the last digit of the current year, '
        'except in case of a consolidated customs initiated in the previous '
        'year of the original request for a rectification.\n'
        ' - 6 digits of the progressive numbering of the custom.',
        string='Customs number',
        copy=False)
    l10n_mx_edi_umt_aduana_id = fields.Many2one(
        comodel_name='uom.uom',
        string="UMT Aduana",
        readonly=True, store=True, compute_sudo=True,
        related='product_id.l10n_mx_edi_umt_aduana_id',
        help="Used in complement 'Comercio Exterior' to indicate in the products the TIGIE Units of Measurement. "
             "It is based in the SAT catalog.")
    l10n_mx_edi_qty_umt = fields.Float(
        string="Qty UMT",
        digits='Product Unit of Measure',
        readonly=False, store=True,
        compute='_compute_l10n_mx_edi_qty_umt',
        help="Quantity expressed in the UMT from product. It is used in the attribute 'CantidadAduana' in the CFDI")
    l10n_mx_edi_price_unit_umt = fields.Float(
        string="Unit Value UMT",
        readonly=True, store=True,
        compute='_compute_l10n_mx_edi_price_unit_umt',
        help="Unit value expressed in the UMT from product. It is used in the attribute 'ValorUnitarioAduana' in the "
             "CFDI")

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_get_custom_numbers(self):
        self.ensure_one()
        if self.l10n_mx_edi_customs_number:
            return [num.strip() for num in self.l10n_mx_edi_customs_number.split(',')]
        else:
            return []

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_mx_edi_umt_aduana_id', 'product_uom_id')
    def _compute_l10n_mx_edi_qty_umt(self):
        for line in self:
            product_aduana_code = line.l10n_mx_edi_umt_aduana_id.l10n_mx_edi_code_aduana
            uom_aduana_code = line.product_uom_id.l10n_mx_edi_code_aduana
            if product_aduana_code == uom_aduana_code:
                line.l10n_mx_edi_qty_umt = line.quantity
            elif '01' in (product_aduana_code or ''):
                line.l10n_mx_edi_qty_umt = round(line.product_id.weight * line.quantity, 3)
            else:
                line.l10n_mx_edi_qty_umt = None

    @api.depends('quantity', 'price_unit', 'l10n_mx_edi_qty_umt')
    def _compute_l10n_mx_edi_price_unit_umt(self):
        for line in self:
            if line.l10n_mx_edi_qty_umt:
                line.l10n_mx_edi_price_unit_umt = round(line.quantity * line.price_unit / line.l10n_mx_edi_qty_umt, 2)
            else:
                line.l10n_mx_edi_price_unit_umt = line.price_unit

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('l10n_mx_edi_customs_number')
    def _check_l10n_mx_edi_customs_number(self):
        invalid_lines = self.env['account.move.line']
        for line in self:
            custom_numbers = line._l10n_mx_edi_get_custom_numbers()
            if any(not CUSTOM_NUMBERS_PATTERN.match(custom_number) for custom_number in custom_numbers):
                invalid_lines |= line

        if not invalid_lines:
            return

        raise ValidationError(_(
            "Custom numbers set on invoice lines are invalid and should have a pattern like: 15  48  3009  0001234:\n%(invalid_message)s",
            invalid_message='\n'.join('%s (id=%s)' % (line.l10n_mx_edi_customs_number, line.id) for line in invalid_lines),
        ))
