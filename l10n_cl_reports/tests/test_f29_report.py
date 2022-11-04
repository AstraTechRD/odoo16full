# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestF29Reports(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_cl.cl_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.partner_a.write({
            'country_id': cls.env.ref('base.cl').id,
            'l10n_cl_sii_taxpayer_type': '1',
            'vat': 'CL762012243',
        })
        cl_account_310115 = cls.env['account.account'].search([('company_id', '=', cls.company_data['company'].id), ('code', '=', '310115')]).id
        cl_account_410230 = cls.env['account.account'].search([('company_id', '=', cls.company_data['company'].id), ('code', '=', '410230')]).id
        cl_purchase_tax = cls.env['account.tax'].search([('name', '=', 'IVA Compra 19% Activo Fijo'), ('company_id', '=', cls.company_data['company'].id)])

        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-01-01',
            'date': '2022-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'account_id': cl_account_310115,
                    'product_id': cls.product_a.id,
                    'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                })
            ],
        })
        vendor_bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-01-01',
            'date': '2022-01-01',
            'l10n_latam_document_type_id': cls.env['l10n_latam.document.type'].search([
                ('code', '=', '46'),
                ('country_id.code', '=', 'CL')
            ]).id,
            'l10n_latam_document_number': 10,
            'invoice_line_ids': [
                (0, 0, {
                    'account_id': cl_account_410230,
                    'product_id': cls.product_a.id,
                    'tax_ids': [Command.set(cl_purchase_tax.ids)],
                    'quantity': 3.0,
                    'price_unit': 400.0,
                })
            ],
        })
        invoice.action_post()
        vendor_bill.action_post()

    @freeze_time('2022-12-31')
    def test_whole_report(self):
        report = self.env.ref('l10n_cl_reports.account_financial_report_f29')
        options = self._generate_options(report, date_from=fields.Date.from_string('2022-01-01'), date_to=fields.Date.from_string('2022-12-31'))
        # pylint: disable=bad-whitespace
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Line Title                                                              Value
            [   0,                                                                         1],
            [
                ('Base Imponible Ventas',                                                 ''),
                ('Ventas Netas Gravadas IVA',                                         1000.0),
                ('Ventas Exentas',                                                        ''),
                ('Factor de Proporción Propuesto (%)',                                    ''),
                ('Total Ventas',                                                      1000.0),
                ('Impuestos Originados por la Venta',                                     ''),
                ('IVA Debito Fiscal',                                                  190.0),  # 19% tax of 1000
                ('Base Imponible Compras',                                                ''),
                ('Compras Netas Gravadas IVA Recuperable',                            1200.0),
                ('Compra Netas Gravadas IVA Uso Comun',                                   ''),
                ('Compras Iva No Recuperable',                                            ''),
                ('Compras Supermercado',                                                  ''),
                ('Compras de Activo Fijo',                                                ''),
                ('Compras No Gravadas Con Iva',                                           ''),
                ('Total Neto Compras',                                                1200.0),
                ('Impuestos Pagados en la Compra',                                        ''),
                ('IVA Pagado Compras Recuperables',                                       ''),
                ('IVA Uso Comun',                                                         ''),
                ('IVA Compras Supermercado',                                              ''),
                ('IVA Compras Activo Fijo Destinados a Ventas Exentas',                228.0),  # 19% tax of 3*400
                ('IVA Compras Activo Fijo Uso Comun',                                     ''),
                ('IVA Compras Activo Fijo No Recuperables',                               ''),
                ('Base IVA Credito Fiscal Afectada por FP',                               ''),
                ('IVA Recuperable',                                                       ''),
                ('IVA Uso Comun',                                                         ''),
                ('IVA Compras Supermercado Uso Comun',                                    ''),
                ('IVA Compras Activo Fijo Destinados Ventas Exentas',                     ''),
                ('IVA Compras Activo Fijo Ventas Uso Comun',                              ''),
                ('IVA Compras Activo Fijo Ventas No Recuperables',                        ''),
                ('Totales',                                                               ''),
                ('IVA Credito Fiscal',                                                 228.0),
                ('IVA a Pagar (Negativo: Saldo a Favor de la Compañía)',               -38.0),  # 190-228
                ('Remanente de CF',                                                       ''),
                ('Impuesto a los Trabajadores',                                           ''),
                ('Retencion Honorarios',                                                  ''),
                ('Tasa de PPM (%)',                                                       ''),
                ('PPM',                                                                   ''),
                ('Total de Impuesto Periodo (Negativo: Saldo a Favor de la Compañía)', -38.0),
            ],
        )

    @freeze_time('2022-12-31')
    def test_report_external_values(self):
        report = self.env.ref('l10n_cl_reports.account_financial_report_f29')
        options = self._generate_options(report, date_from=fields.Date.from_string('2022-01-01'), date_to=fields.Date.from_string('2022-12-31'))
        fpp_rate = self.env['account.report.external.value'].create({
            'company_id': self.env.company.id,
            'target_report_expression_id': self.env.ref('l10n_cl_reports.account_financial_report_f29_line_0103_balance').id,
            'name': 'Manual value',
            'date': fields.Date.from_string('2022-12-31'),
            'value': 10,
        })
        ppm_rate = self.env['account.report.external.value'].create({
            'company_id': self.env.company.id,
            'target_report_expression_id': self.env.ref('l10n_cl_reports.account_financial_report_f29_line_0606_balance').id,
            'name': 'Manual value',
            'date': fields.Date.from_string('2022-12-31'),
            'value': 25,
        })
        # pylint: disable=bad-whitespace
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Line Title                                                              Value
            [   0,                                                                         1],
            [
                ('Base Imponible Ventas',                                                 ''),
                ('Ventas Netas Gravadas IVA',                                         1000.0),
                ('Ventas Exentas',                                                        ''),
                ('Factor de Proporción Propuesto (%)',                                 '10.0%'),  # FPP rate
                ('Total Ventas',                                                      1000.0),
                ('Impuestos Originados por la Venta',                                     ''),
                ('IVA Debito Fiscal',                                                  190.0),  # 19% tax of 1000
                ('Base Imponible Compras',                                                ''),
                ('Compras Netas Gravadas IVA Recuperable',                            1200.0),
                ('Compra Netas Gravadas IVA Uso Comun',                                   ''),
                ('Compras Iva No Recuperable',                                            ''),
                ('Compras Supermercado',                                                  ''),
                ('Compras de Activo Fijo',                                                ''),
                ('Compras No Gravadas Con Iva',                                           ''),
                ('Total Neto Compras',                                                1200.0),
                ('Impuestos Pagados en la Compra',                                        ''),
                ('IVA Pagado Compras Recuperables',                                       ''),
                ('IVA Uso Comun',                                                         ''),
                ('IVA Compras Supermercado',                                              ''),
                ('IVA Compras Activo Fijo Destinados a Ventas Exentas',                228.0),  # 19% tax of 3*400
                ('IVA Compras Activo Fijo Uso Comun',                                     ''),
                ('IVA Compras Activo Fijo No Recuperables',                               ''),
                ('Base IVA Credito Fiscal Afectada por FP',                               ''),
                ('IVA Recuperable',                                                       ''),
                ('IVA Uso Comun',                                                         ''),
                ('IVA Compras Supermercado Uso Comun',                                    ''),
                ('IVA Compras Activo Fijo Destinados Ventas Exentas',                   23.0),  # FPP rate 10% of 228 (rounded because of currency decimal_places of 0)
                ('IVA Compras Activo Fijo Ventas Uso Comun',                              ''),
                ('IVA Compras Activo Fijo Ventas No Recuperables',                        ''),
                ('Totales',                                                               ''),
                ('IVA Credito Fiscal',                                                 228.0),
                ('IVA a Pagar (Negativo: Saldo a Favor de la Compañía)',               -38.0),  # 190-228
                ('Remanente de CF',                                                       ''),
                ('Impuesto a los Trabajadores',                                           ''),
                ('Retencion Honorarios',                                                  ''),
                ('Tasa de PPM (%)',                                                    '25.0%'),  # PPM rate
                ('PPM',                                                                250.0),  # PPM rate 25% of 1000
                ('Total de Impuesto Periodo (Negativo: Saldo a Favor de la Compañía)', 212.0),  # 250 - 38
            ],
        )
        fpp_rate.write({'value': 20})
        ppm_rate.write({'value': 30})
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Line Title                                                              Value
            [   0,                                                                         1],
            [
                ('Base Imponible Ventas',                                                 ''),
                ('Ventas Netas Gravadas IVA',                                         1000.0),
                ('Ventas Exentas',                                                        ''),
                ('Factor de Proporción Propuesto (%)',                                 '20.0%'),  # FPP rate
                ('Total Ventas',                                                      1000.0),
                ('Impuestos Originados por la Venta',                                     ''),
                ('IVA Debito Fiscal',                                                  190.0),  # 19% tax of 1000
                ('Base Imponible Compras',                                                ''),
                ('Compras Netas Gravadas IVA Recuperable',                            1200.0),
                ('Compra Netas Gravadas IVA Uso Comun',                                   ''),
                ('Compras Iva No Recuperable',                                            ''),
                ('Compras Supermercado',                                                  ''),
                ('Compras de Activo Fijo',                                                ''),
                ('Compras No Gravadas Con Iva',                                           ''),
                ('Total Neto Compras',                                                1200.0),
                ('Impuestos Pagados en la Compra',                                        ''),
                ('IVA Pagado Compras Recuperables',                                       ''),
                ('IVA Uso Comun',                                                         ''),
                ('IVA Compras Supermercado',                                              ''),
                ('IVA Compras Activo Fijo Destinados a Ventas Exentas',                228.0),  # 19% tax of 3*400
                ('IVA Compras Activo Fijo Uso Comun',                                     ''),
                ('IVA Compras Activo Fijo No Recuperables',                               ''),
                ('Base IVA Credito Fiscal Afectada por FP',                               ''),
                ('IVA Recuperable',                                                       ''),
                ('IVA Uso Comun',                                                         ''),
                ('IVA Compras Supermercado Uso Comun',                                    ''),
                ('IVA Compras Activo Fijo Destinados Ventas Exentas',                   46.0),  # FPP rate 20% of 228 (rounded because of currency decimal_places of 0)
                ('IVA Compras Activo Fijo Ventas Uso Comun',                              ''),
                ('IVA Compras Activo Fijo Ventas No Recuperables',                        ''),
                ('Totales',                                                               ''),
                ('IVA Credito Fiscal',                                                 228.0),
                ('IVA a Pagar (Negativo: Saldo a Favor de la Compañía)',               -38.0),  # 190-228
                ('Remanente de CF',                                                       ''),
                ('Impuesto a los Trabajadores',                                           ''),
                ('Retencion Honorarios',                                                  ''),
                ('Tasa de PPM (%)',                                                    '30.0%'),  # PPM rate
                ('PPM',                                                                300.0),  # PPM rate 30% of 1000
                ('Total de Impuesto Periodo (Negativo: Saldo a Favor de la Compañía)', 262.0),  # 300 - 38
            ],
        )
