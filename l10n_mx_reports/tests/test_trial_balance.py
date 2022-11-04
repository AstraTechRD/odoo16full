# -*- coding: utf-8 -*-
# pylint: disable=C0326
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged
from odoo.exceptions import RedirectWarning

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nMXTrialBalanceReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_mx.mx_coa'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].country_id = cls.env.ref('base.mx')
        cls.company_data['company'].vat = 'EKU9003173C9'

        # Entries in 2020 to test initial balance
        cls.move_2020_01 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.to_date('2020-01-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({'debit': 1000.0, 'credit': 0.0, 'account_id': cls.company_data['default_account_payable'].id}),
                Command.create({'debit': 0.0, 'credit': 1000.0, 'account_id': cls.company_data['default_account_revenue'].id}),
            ]
        })

        cls.move_2020_02 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.to_date('2020-02-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create(
                    {'debit': 500.0, 'credit': 0.0, 'account_id': cls.company_data['default_account_expense'].id}),
                Command.create(
                    {'debit': 0.0, 'credit': 500.0, 'account_id': cls.company_data['default_account_revenue'].id}),
            ]
        })
        (cls.move_2020_01 + cls.move_2020_02).action_post()

        # Entries in 2021 to test report for a specific financial year
        cls.move_2021_01 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.to_date('2021-06-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create(
                    {'debit': 250.0, 'credit': 0.0, 'account_id': cls.company_data['default_account_expense'].id}),
                Command.create(
                    {'debit': 0.0, 'credit': 250.0, 'account_id': cls.company_data['default_account_revenue'].id}),
            ]
        })

        cls.move_2021_02 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.to_date('2021-08-01'),
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create(
                    {'debit': 75.0, 'credit': 0.0, 'account_id': cls.company_data['default_account_payable'].id}),
                Command.create(
                    {'debit': 0.0, 'credit': 75.0, 'account_id': cls.company_data['default_account_revenue'].id}),
            ]
        })
        (cls.move_2021_01 + cls.move_2021_02).action_post()

        cls.report = cls.env.ref('account_reports.trial_balance_report')

    def test_generate_coa_xml(self):
        """ This test will generate a COA report and verify that every
            account with an entry in the selected period has been there.

            CodAgrup corresponds to Account Group code
            NumCta corresponds to Account Group code
            Desc corresponds to Account Group Name
            Nivel corresponds to Hierarchy Level
            Natur corresponds to type of account (Debit or Credit)

            Available values for "Natur":
            D = Debit Account
            A = Credit Account

            Unaffected Earnings account is not include in this report because
            it's custom Odoo account.
        """
        expected_coa_xml = b"""<?xml version='1.0' encoding='utf-8'?>
        <catalogocuentas:Catalogo xmlns:catalogocuentas="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas/CatalogoCuentas_1_3.xsd" Version="1.3" RFC="EKU9003173C9" Mes="01" Anio="2021">
            <catalogocuentas:Ctas CodAgrup="201" NumCta="201" Desc="Proveedores" Nivel="1" Natur="A"/>
            <catalogocuentas:Ctas CodAgrup="201.01" NumCta="201.01" Desc="Proveedores nacionales" Nivel="2" Natur="A"/>
            <catalogocuentas:Ctas CodAgrup="401" NumCta="401" Desc="Ingresos" Nivel="1" Natur="A"/>
            <catalogocuentas:Ctas CodAgrup="401.01" NumCta="401.01" Desc="Ventas y/o servicios gravados a la tasa general" Nivel="2" Natur="A"/>
            <catalogocuentas:Ctas CodAgrup="601" NumCta="601" Desc="Gastos generales" Nivel="1" Natur="D"/>
            <catalogocuentas:Ctas CodAgrup="601.84" NumCta="601.84" Desc="Otros gastos generales" Nivel="2" Natur="D"/>
        </catalogocuentas:Catalogo>
        """

        options = self._generate_options(self.report, '2021-01-01', '2021-12-31')
        coa_report = self.env[self.report.custom_handler_model_name].with_context(skip_xsd=True).action_l10n_mx_generate_coa_sat_xml(options)['file_content']
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(coa_report),
            self.get_xml_tree_from_string(expected_coa_xml),
        )

    def test_generate_sat_xml(self):
        """ This test will generate a SAT report and verify that
        every account present in the trial balance (except unaffected
        earnings account) is present in the xml.

        SaldoIni corresponds to Initial Balance
        SaldoFin corresponds to End Balance
        Debe corresponds to Debit in the current period
        Haber corresponds to Credit in the current period
        NumCta corresponds to Account Group code
        """
        expected_sat_xml = b"""<?xml version='1.0' encoding='utf-8'?>
        <BCE:Balanza xmlns:BCE="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion/BalanzaComprobacion_1_3.xsd" Version="1.3" RFC="EKU9003173C9" Mes="01" Anio="2021" TipoEnvio="N">
            <BCE:Ctas Debe="75.00" NumCta="201" Haber="0.00" SaldoFin="1075.00" SaldoIni="1000.00"/>
            <BCE:Ctas Debe="75.00" NumCta="201.01" Haber="0.00" SaldoFin="1075.00" SaldoIni="1000.00"/>
            <BCE:Ctas Debe="0.00" NumCta="401" Haber="325.00" SaldoFin="-325.00" SaldoIni="0.00"/>
            <BCE:Ctas Debe="0.00" NumCta="401.01" Haber="325.00" SaldoFin="-325.00" SaldoIni="0.00"/>
            <BCE:Ctas Debe="250.00" NumCta="601" Haber="0.00" SaldoFin="250.00" SaldoIni="0.00"/>
            <BCE:Ctas Debe="250.00" NumCta="601.84" Haber="0.00" SaldoFin="250.00" SaldoIni="0.00"/>
        </BCE:Balanza>
        """

        options = self._generate_options(self.report, '2021-01-01', '2021-12-31')
        sat_report = self.env[self.report.custom_handler_model_name].with_context(skip_xsd=True).action_l10n_mx_generate_sat_xml(options)['file_content']
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(sat_report),
            self.get_xml_tree_from_string(expected_sat_xml),
        )

    def test_generate_coa_xml_without_tag(self):
        """This test verifies that all accounts present in the trial balance have a Debit or a Credit balance account tag"""
        self.company_data['default_account_payable'].tag_ids = [Command.clear()]
        options = self._generate_options(self.report, '2021-01-01', '2021-12-31')
        with self.assertRaises(RedirectWarning):
            self.env[self.report.custom_handler_model_name].action_l10n_mx_generate_coa_sat_xml(options)

    def test_generate_coa_xml_with_too_much_tag(self):
        """This test verifies that all accounts present in the trial balance have exactly one Debit or Credit balance account tag"""
        self.company_data['default_account_payable'].tag_ids = self.env.ref('l10n_mx.tag_debit_balance_account') + self.env.ref('l10n_mx.tag_credit_balance_account')
        options = self._generate_options(self.report, '2021-01-01', '2021-12-31')
        with self.assertRaises(RedirectWarning):
            self.env[self.report.custom_handler_model_name].action_l10n_mx_generate_coa_sat_xml(options)

    def test_mx_trial_balance(self):
        """ This test will test the Mexican Trial Balance (with and without the hierarchy) """
        # Testing the report without hierarchy
        options = self._generate_options(self.report, '2021-01-01', '2021-12-31', {'hierarchy': False, 'unfold_all': True})
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,         2,         3,       4,        5,         6],
            [
                ('201.01.01 Proveedores nacionales',                          1000.0,    '',        75.0,    '',       1075.0,    ''),
                ('401.01.01 Ventas y/o servicios gravados a la tasa general', '',        '',        '',      325.0,    '',        325.0),
                ('601.84.01 Otros gastos generales',                          '',        '',        250.0,   '',       250.0,     ''),
                ('999999 Undistributed Profits/Losses',                       '',        1000.0,    '',      '',       '',        1000.0),
                ('Total',                                                     1000.0,    1000.0,    325.0,   325.0,    1325.0,    1325.0),
            ],
        )

        # Testing the report with hierarchy
        options['hierarchy'] = True
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,         2,         3,       4,        5,         6],
            [
                ('2 Pasivos',                                                 1000.0,    '',        75.0,    '',       1075.0,    ''),
                ('201 Proveedores',                                           1000.0,    '',        75.0,    '',       1075.0,    ''),
                ('201.01 Proveedores nacionales',                             1000.0,    '',        75.0,    '',       1075.0,    ''),
                ('201.01.01 Proveedores nacionales',                          1000.0,    '',        75.0,    '',       1075.0,    ''),
                ('4 Ingresos',                                                '',        '',        '',      325.0,    '',        325.0),
                ('401 Ingresos',                                              '',        '',        '',      325.0,    '',        325.0),
                ('401.01 Ventas y/o servicios gravados a la tasa general',    '',        '',        '',      325.0,    '',        325.0),
                ('401.01.01 Ventas y/o servicios gravados a la tasa general', '',        '',        '',      325.0,    '',        325.0),
                ('6 Gastos',                                                  '',        '',        250.0,   '',       250.0,     ''),
                ('601 Gastos generales',                                      '',        '',        250.0,   '',       250.0,     ''),
                ('601.84 Otros gastos generales',                             '',        '',        250.0,   '',       250.0,     ''),
                ('601.84.01 Otros gastos generales',                          '',        '',        250.0,   '',       250.0,     ''),
                ('(No Group)',                                                '',        1000.0,    '',      '',       '',        1000.0),
                ('999999 Undistributed Profits/Losses',                       '',        1000.0,    '',      '',       '',        1000.0),
                ('Total',                                                     1000.0,    1000.0,    325.0,   325.0,    1325.0,    1325.0),
            ],
        )
