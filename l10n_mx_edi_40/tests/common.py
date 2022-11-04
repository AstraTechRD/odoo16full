# coding: utf-8
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged
from odoo.tools import misc

import base64
import datetime

from freezegun import freeze_time
from pytz import timezone


def mocked_l10n_mx_edi_pac(edi_format, invoice, exported):
    exported['cfdi_signed'] = exported['cfdi_str']
    exported['cfdi_encoding'] = 'str'
    return exported


class TestMxEdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_mx.mx_coa', edi_format_ref='l10n_mx_edi.edi_cfdi_3_3'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime.datetime(year=2017, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====

        cls.certificate = cls.env['l10n_mx_edi.certificate'].create({
            'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
            'key': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
            'password': '12345678a',
        })
        cls.certificate.write({
            'date_start': '2016-01-01 01:00:00',
            'date_end': '2018-01-01 01:00:00',
        })

        cls.company_values = {
            'vat': 'EKU9003173C9',
            'street': 'Campobasso Norte 3206 - 9000',
            'street2': 'Fraccionamiento Montecarlo',
            'zip': '85134',
            'city': 'Ciudad Obregón',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_son').id,
            'l10n_mx_edi_pac': 'solfact',
            'l10n_mx_edi_pac_test_env': True,
            'l10n_mx_edi_fiscal_regime': '601',
            'l10n_mx_edi_certificate_ids': [(6, 0, cls.certificate.ids)],
        }
        cls.company_data['company'].write(cls.company_values)

        cls.currency_data['currency'].l10n_mx_edi_decimal_places = 3

        # Rename USD to something else and create a new USD with defined rates.
        # Done like this because currencies should be fetched by name, not by xml_id
        cls.env.ref('base.USD').name = 'FUSD'
        cls.env['res.currency'].flush_model(['name'])
        cls.fake_usd_data = cls.setup_multi_currency_data(default_values={
            'name': 'USD',
            'symbol': '$',
            'rounding': 0.01,
            'l10n_mx_edi_decimal_places': 2,
        }, rate2016=6.0, rate2017=4.0)

        # Prevent the xsd validation because it could lead to a not-deterministic behavior since the xsd is downloaded
        # by a CRON.
        xsd_attachment = cls.env.ref('l10n_mx_edi.xsd_cached_cfdv33_xsd', False)
        if xsd_attachment:
            xsd_attachment.unlink()

        # ==== Business ====

        cls.tax_16 = cls.env['account.tax'].create({
            'name': 'tax_16',
            'amount_type': 'percent',
            'amount': 16,
            'type_tax_use': 'sale',
            'l10n_mx_tax_type': 'Tasa',
        })

        cls.tax_10_negative = cls.env['account.tax'].create({
            'name': 'tax_10_negative',
            'amount_type': 'percent',
            'amount': -10,
            'type_tax_use': 'sale',
            'l10n_mx_tax_type': 'Tasa',
        })

        cls.tax_group = cls.env['account.tax'].create({
            'name': 'tax_group',
            'amount_type': 'group',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'children_tax_ids': [(6, 0, (cls.tax_16 + cls.tax_10_negative).ids)],
        })

        cls.product = cls.env['product.product'].create({
            'name': 'product_mx',
            'weight': 2,
            'uom_po_id': cls.env.ref('uom.product_uom_kgm').id,
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_01010101').id,
        })

        cls.payment_term = cls.env['account.payment.term'].create({
            'name': 'test l10n_mx_edi',
            'line_ids': [(0, 0, {
                'value': 'balance',
                'value_amount': 0.0,
                'days': 90,
            })],
        })

        cls.partner_a.write({
            'property_supplier_payment_term_id': cls.payment_term.id,
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_23').id,
            'zip': 39301,
            'vat': '123456789',
            'l10n_mx_edi_no_tax_breakdown': False,
            'l10n_mx_edi_fiscal_regime': '616',
        })

        # ==== Records needing CFDI ====

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'invoice_date_due': '2017-01-01',
            'invoice_payment_term_id': False,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_incoterm_id': cls.env.ref('account.incoterm_FCA').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, (cls.tax_16 + cls.tax_10_negative).ids)],
            })],
        })

        cls.credit_note = cls.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_payment_term_id': False,
            'date': '2017-01-01',
            'currency_id': cls.currency_data['currency'].id,
            'invoice_incoterm_id': cls.env.ref('account.incoterm_FCA').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, (cls.tax_16 + cls.tax_10_negative).ids)],
            })],
        })

        cls.expected_invoice_cfdi_values = '''
            <Comprobante
                Certificado="___ignore___"
                Fecha="2017-01-01T17:00:00"
                Folio="1"
                FormaPago="99"
                LugarExpedicion="85134"
                MetodoPago="PUE"
                Moneda="Gol"
                NoCertificado="''' + cls.certificate.serial_number + '''"
                Serie="INV/2017/"
                Sello="___ignore___"
                Descuento="2000.000"
                SubTotal="10000.000"
                Total="8480.000"
                TipoCambio="0.500000"
                TipoDeComprobante="I"
                Exportacion="01"
                Version="4.0">
                <Emisor
                    Rfc="EKU9003173C9"
                    Nombre="COMPANY_1_DATA"
                    RegimenFiscal="601"/>
                <Receptor
                    Rfc="XEXX010101000"
                    Nombre="PARTNER_A"
                    DomicilioFiscalReceptor="85134"
                    RegimenFiscalReceptor="616"
                    UsoCFDI="S01"/>
                <Conceptos>
                    <Concepto
                        Cantidad="5.000000"
                        ClaveProdServ="01010101"
                        Descripcion="product_mx"
                        ObjetoImp="02"
                        Importe="10000.000"
                        Descuento="2000.000"
                        ClaveUnidad="KGM"
                        Unidad="KG"
                        ValorUnitario="2000.000">
                        <Impuestos>
                            <Traslados>
                                <Traslado
                                    Base="8000.000"
                                    Importe="1280.00"
                                    TasaOCuota="0.160000"
                                    TipoFactor="Tasa"/>
                            </Traslados>
                            <Retenciones>
                                <Retencion
                                    Base="8000.000"
                                    Importe="800.00"
                                    TasaOCuota="0.100000"
                                    TipoFactor="Tasa"/>
                            </Retenciones>
                        </Impuestos>
                    </Concepto>
                </Conceptos>
                <Impuestos
                    TotalImpuestosRetenidos="800.000"
                    TotalImpuestosTrasladados="1280.000">
                    <Retenciones>
                        <Retencion
                            Importe="800.000"/>
                    </Retenciones>
                    <Traslados>
                        <Traslado
                            Base="8000.000"
                            Importe="1280.000"
                            TasaOCuota="0.160000"
                            TipoFactor="Tasa"/>
                    </Traslados>
                </Impuestos>
            </Comprobante>
        '''

        cls.payment = cls.env['account.payment'].create({
            'date': '2017-01-01',
            'amount': cls.invoice.amount_total,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'payment_method_line_id': cls.outbound_payment_method_line.payment_method_id.id,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })

        with freeze_time(cls.frozen_today):
            cls.statement_line = cls.env['account.bank.statement.line'].create({
                'journal_id': cls.company_data['default_journal_bank'].id,
                'payment_ref': 'mx_st_line',
                'partner_id': cls.partner_a.id,
                'foreign_currency_id': cls.currency_data['currency'].id,
                'amount': cls.invoice.amount_total_signed,
                'amount_currency': cls.invoice.amount_total,
                'date': '2017-01-01',
            })

        # payment done on 2017-01-01 00:00:00 UTC is expected to be signed on 2016-12-31 17:00:00 in Mexico tz
        cls.expected_payment_cfdi_values = '''
            <Comprobante
                Certificado="___ignore___"
                Fecha="2016-12-31T17:00:00"
                Folio="1"
                LugarExpedicion="85134"
                Moneda="XXX"
                NoCertificado="''' + cls.certificate.serial_number + '''"
                Serie="PBNK1/2017/"
                Sello="___ignore___"
                SubTotal="0"
                Total="0"
                TipoDeComprobante="P"
                Exportacion="01"
                Version="4.0">
                <Emisor
                    Rfc="EKU9003173C9"
                    Nombre="COMPANY_1_DATA"
                    RegimenFiscal="601"/>
                <Receptor
                    Rfc="XEXX010101000"
                    Nombre="PARTNER_A"
                    ResidenciaFiscal="USA"
                    RegimenFiscalReceptor="616"
                    DomicilioFiscalReceptor="85134"
                    UsoCFDI="CP01"/>
                <Conceptos>
                    <Concepto
                        Cantidad="1"
                        ClaveProdServ="84111506"
                        ClaveUnidad="ACT"
                        Descripcion="Pago"
                        Importe="0"
                        ObjetoImp="01"
                        ValorUnitario="0"/>
                </Conceptos>
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales
                            MontoTotalPagos="4240.00"/>
                        <Pago
                            FechaPago="2017-01-01T12:00:00"
                            MonedaP="Gol"
                            Monto="8480.000"
                            FormaDePagoP="99"
                            TipoCambioP="0.500000">
                            <DoctoRelacionado
                                Folio="1"
                                IdDocumento="123456789"
                                ImpPagado="8480.000"
                                ImpSaldoAnt="8480.000"
                                ImpSaldoInsoluto="0.000"
                                ObjetoImpDR="03"
                                EquivalenciaDR="1"
                                MonedaDR="Gol"
                                NumParcialidad="1"
                                Serie="INV/2017/"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            </Comprobante>
        '''
