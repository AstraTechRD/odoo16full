# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon, mocked_l10n_mx_edi_pac
from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from freezegun import freeze_time
from unittest.mock import patch


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCfdiPaymentMultiCurrencies(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.comp_curr = cls.company_data['currency']
        cls.foreign_curr_1 = cls.currency_data['currency'] # 3:1 in 2016, 2:1 in 2017
        cls.foreign_curr_2 = cls.fake_usd_data['currency'] # 6:1 in 2016, 4:1 in 2017

    def create_invoice(self, invoice_date, currency, amount):
        invoice = self.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_date': invoice_date,
            'date': invoice_date,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'price_unit': amount,
                'tax_ids': [],
            })],
        })
        invoice.action_post()
        return invoice

    def create_payment(self, payment_date, currency, amount, invoices, **kwargs):
        return self.env['account.payment.register']\
            .with_context(
                active_model='account.move',
                active_ids=invoices.ids,
                default_l10n_mx_edi_force_generate_cfdi=True,
            )\
            .create({
                'amount': amount,
                'payment_date': payment_date,
                'currency_id': currency.id,
                'group_payment': True,
                **kwargs,
            })\
            ._create_payments()

    def assertCfdiValues(self, payment, invoices, complemento):
        for i, invoice in enumerate(invoices):
            self._process_documents_web_services(invoice)
            invoice.l10n_mx_edi_cfdi_uuid = f'12345{i}'
        generated_files = self._process_documents_web_services(payment.move_id, {'cfdi_3_3'})
        self.assertTrue(generated_files)
        cfdi = generated_files[0]
        current_etree = self.get_xml_tree_from_string(cfdi)
        expected_etree = self.with_applied_xpath(
            self.get_xml_tree_from_string(self.expected_payment_cfdi_values),
            f'''
                <xpath expr="//Comprobante" position="attributes">
                    <attribute name="Folio">___ignore___</attribute>
                    <attribute name="Serie">___ignore___</attribute>
                </xpath>
                <xpath expr="//Complemento" position="replace">{complemento}</xpath>
            ''',
        )
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_payment_cfdi_pay_mxn_inv_mxn(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice1 = self.create_invoice('2017-01-01', self.comp_curr, 1200.0)
            invoice2 = self.create_invoice('2017-01-01', self.comp_curr, 1200.0)
            payment = self.create_payment('2017-01-01', self.comp_curr, 2400.0, invoice1 + invoice2)
            self.assertCfdiValues(payment, invoice1 + invoice2, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="2400.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="MXN"
                            Monto="2400.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="1">
                            <DoctoRelacionado
                                IdDocumento="___ignore___"
                                Folio="___ignore___"
                                Serie="___ignore___"
                                ImpPagado="1200.00"
                                ImpSaldoAnt="1200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                EquivalenciaDR="1"
                                MonedaDR="MXN"
                                NumParcialidad="1">
                            </DoctoRelacionado>
                            <DoctoRelacionado
                                IdDocumento="___ignore___"
                                Folio="___ignore___"
                                Serie="___ignore___"
                                ImpPagado="1200.00"
                                ImpSaldoAnt="1200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                EquivalenciaDR="1"
                                MonedaDR="MXN"
                                NumParcialidad="1">
                            </DoctoRelacionado>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_usd_inv_usd(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice1 = self.create_invoice('2017-01-01', self.foreign_curr_2, 1200.0)
            invoice2 = self.create_invoice('2016-01-01', self.foreign_curr_2, 1200.0)
            payment = self.create_payment('2017-01-01', self.foreign_curr_2, 2400.0, invoice1 + invoice2)
            self.assertCfdiValues(payment, invoice1 + invoice2, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="600.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="USD"
                            Monto="2400.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="0.250000">
                            <DoctoRelacionado
                                IdDocumento="___ignore___"
                                Folio="___ignore___"
                                Serie="___ignore___"
                                ImpPagado="1200.00"
                                ImpSaldoAnt="1200.00"
                                ImpSaldoInsoluto="0.00"
                                EquivalenciaDR="1"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                NumParcialidad="1"/>
                            <DoctoRelacionado
                                IdDocumento="___ignore___"
                                Folio="___ignore___"
                                Serie="___ignore___"
                                ImpPagado="1200.00"
                                ImpSaldoAnt="1200.00"
                                ImpSaldoInsoluto="0.00"
                                EquivalenciaDR="1"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                NumParcialidad="1"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_mxn_inv_usd_1(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice = self.create_invoice('2016-01-01', self.foreign_curr_2, 7200.0) # = 1200 MXN
            payment = self.create_payment('2017-01-01', self.comp_curr, 1800.0, invoice) # = 7200.0 USD
            self.assertCfdiValues(payment, invoice, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="1800.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="MXN"
                            Monto="1800.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="1">
                            <DoctoRelacionado
                                Folio="___ignore___"
                                Serie="___ignore___"
                                IdDocumento="___ignore___"
                                ImpPagado="7200.00"
                                ImpSaldoAnt="7200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                EquivalenciaDR="4.000000"
                                NumParcialidad="1"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_mxn_inv_usd_2(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice = self.create_invoice('2017-01-01', self.foreign_curr_2, 7200.0) # = 1600 MXN
            payment = self.create_payment('2016-01-01', self.comp_curr, 1200.0, invoice) # = 7200 USD
            self.assertCfdiValues(payment, invoice, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="1200.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="MXN"
                            Monto="1200.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="1">
                            <DoctoRelacionado
                                Folio="___ignore___"
                                IdDocumento="___ignore___"
                                ImpPagado="7200.00"
                                ImpSaldoAnt="7200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                EquivalenciaDR="6.000000"
                                NumParcialidad="1"
                                Serie="___ignore___"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_mxn_inv_usd_keep_open(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice = self.create_invoice('2016-01-01', self.foreign_curr_2, 7200.0)  # = 1200 MXN
            payment = self.create_payment('2017-01-01', self.comp_curr, 1200.0, invoice, payment_difference_handling='open')
            self.assertCfdiValues(payment, invoice, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="1200.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="MXN"
                            Monto="1200.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="1">
                            <DoctoRelacionado
                                Folio="___ignore___"
                                IdDocumento="___ignore___"
                                ImpPagado="4800.00"
                                ImpSaldoAnt="7200.00"
                                ImpSaldoInsoluto="2400.00"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                EquivalenciaDR="4.000000"
                                NumParcialidad="1"
                                Serie="___ignore___"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_mxn_inv_usd_writeoff_lower_payment(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice = self.create_invoice('2016-01-01', self.foreign_curr_2, 7200.0) # = 1200 MXN
            payment = self.create_payment(
                '2017-01-01', self.comp_curr, 1200.0, invoice,
                payment_difference_handling='reconcile',
                writeoff_account_id=self.company_data['default_account_revenue'].id,
                writeoff_label="write-off",
            )
            self.assertCfdiValues(payment, invoice, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="1800.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="MXN"
                            Monto="1800.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="1">
                            <DoctoRelacionado
                                Folio="___ignore___"
                                IdDocumento="___ignore___"
                                ImpPagado="7200.00"
                                ImpSaldoAnt="7200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                EquivalenciaDR="4.000000"
                                NumParcialidad="1"
                                Serie="___ignore___"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_mxn_inv_usd_writeoff_higher_payment(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            invoice = self.create_invoice('2016-01-01', self.foreign_curr_2, 7200.0) # = 1200 MXN
            payment = self.create_payment(
                '2017-01-01', self.comp_curr, 2400.0, invoice,
                payment_difference_handling='reconcile',
                writeoff_account_id=self.company_data['default_account_revenue'].id,
                writeoff_label="write-off",
            )
            self.assertCfdiValues(payment, invoice, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="1800.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="MXN"
                            Monto="1800.00"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="1">
                            <DoctoRelacionado
                                Folio="___ignore___"
                                IdDocumento="___ignore___"
                                ImpPagado="7200.00"
                                ImpSaldoAnt="7200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                EquivalenciaDR="4.000000"
                                NumParcialidad="1"
                                Serie="___ignore___"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')

    def test_payment_cfdi_pay_usd_inv_gol_2(self):
        with freeze_time(self.frozen_today), \
             mute_logger('py.warnings'), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            # Single currency.
            invoice = self.create_invoice('2017-01-01', self.foreign_curr_2, 7200.0) # = 1800 MXN
            payment = self.create_payment('2016-01-01', self.foreign_curr_1, 5400.0, invoice) # = 1800 MXN
            self.assertCfdiValues(payment, invoice, '''
                <Complemento>
                    <Pagos
                        Version="2.0">
                        <Totales 
                            MontoTotalPagos="1800.00"/>
                        <Pago
                            FechaPago="___ignore___"
                            MonedaP="Gol"
                            Monto="5400.000"
                            NumOperacion="___ignore___"
                            FormaDePagoP="___ignore___"
                            TipoCambioP="0.333334">
                            <DoctoRelacionado
                                Folio="___ignore___"
                                IdDocumento="___ignore___"
                                ImpPagado="7200.00"
                                ImpSaldoAnt="7200.00"
                                ImpSaldoInsoluto="0.00"
                                ObjetoImpDR="01"
                                MonedaDR="USD"
                                EquivalenciaDR="4.000000"
                                NumParcialidad="1"
                                Serie="___ignore___"/>
                        </Pago>
                    </Pagos>
                </Complemento>
            ''')
