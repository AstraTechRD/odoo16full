# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=C0326

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields
from datetime import datetime
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class LuxembourgElectronicReportTest(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_lu.lu_2011_chart_1'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'ecdf_prefix': '1234AB',
            'vat': 'LU12345613',
            'matr_number': '12345678900',
        })

        cls.out_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line_1',
                    'price_unit': 1000.0,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                }),
            ],
        })

        cls.in_invoice = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line_1',
                    'price_unit': 800.0,
                    'quantity': 1.0,
                    'account_id': cls.company_data['default_account_expense'].id,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_purchase'].ids)],
                }),
            ],
        })

        (cls.out_invoice + cls.in_invoice).action_post()
    #
    def _filter_zero_lines(self, lines):
        filtered_lines = []
        for line in lines:
            bal_col = line['columns'][0]
            if not bal_col.get('is_zero'):
                filtered_lines.append(line)
        return filtered_lines

    def test_balance_sheet(self):
        report = self.env.ref('l10n_lu_reports.account_financial_report_l10n_lu_bs')
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self._filter_zero_lines(report._get_lines(options)),
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('D. Current assets',                           1306.0),
                ('II. Debtors',                                 1306.0),
                ('1. Trade debtors',                            1170.0),
                ('a) becoming due and payable within one year', 1170.0),
                ('4. Other debtors',                            136.0),
                ('a) becoming due and payable within one year', 136.0),
                ('TOTAL (ASSETS)',                              1306.0),
                ('A. Capital and reserves',                      200.0),
                ('VI. Profit or loss for the financial year',    200.0),
                ('C. Creditors',                                 1106.0),
                ('4. Trade creditors',                           936.0),
                ('a) becoming due and payable within one year',  936.0),
                ('8. Other creditors',                           170.0),
                ('a) Tax authorities',                           170.0),
                ('TOTAL (CAPITAL, RESERVES AND LIABILITIES)',    1306.0),
            ],
        )

    def test_profit_and_loss(self):
        report = self.env.ref('l10n_lu_reports.account_financial_report_l10n_lu_pl')
        options = self._generate_options(report, fields.Date.from_string('2017-01-01'), fields.Date.from_string('2017-12-31'))

        self.assertLinesValues(
            self._filter_zero_lines(report._get_lines(options)),
            #   Name                                                                    Balance
            [   0,                                                                      1],
            [
                ('1. Net turnover',                                                     1000.0),
                ('5. Raw materials and consumables and other external expenses',        -800.0),
                ('a) Raw materials and consumables',                                    -800.0),
                ('16. Profit or loss after taxation',                                    200.0),
                ('18. Profit or loss for the financial year',                            200.0),
            ],
        )

    @freeze_time('2019-12-31')
    def test_generate_xml(self):
        first_tax = self.env['account.tax'].search([('name', '=', '17-P-G'), ('company_id', '=', self.company_data['company'].id)], limit=1)
        second_tax = self.env['account.tax'].search([('name', '=', '14-P-S'), ('company_id', '=', self.company_data['company'].id)], limit=1)

        # Create and post a move with two move lines to get some data in the report
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-11-12',
            'date': '2019-11-12',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 150,
                'tax_ids': first_tax.ids,
            }), (0, 0, {
                'product_id': self.product_b.id,
                'quantity': 1.0,
                'name': 'product test 2',
                'price_unit': 100,
                'tax_ids': second_tax.ids,
            })]
        })
        move.action_post()

        report = self.env.ref('l10n_lu.tax_report')
        options = report._get_options()

        # Add the filename in the options, which is initially done by the get_report_filename() method
        now_datetime = datetime.now()
        file_ref_data = {
            'ecdf_prefix': self.env.company.ecdf_prefix,
            'datetime': now_datetime.strftime('%Y%m%dT%H%M%S%f')[:-4]
        }
        options['filename'] = '{ecdf_prefix}X{datetime}'.format(**file_ref_data)

        expected_xml = """
        <eCDFDeclarations xmlns="http://www.ctie.etat.lu/2011/ecdf">
            <FileReference>%s</FileReference>
            <eCDFFileVersion>1.1</eCDFFileVersion>
            <Interface>MODL5</Interface>
            <Agent>
                <MatrNbr>12345678900</MatrNbr>
                <RCSNbr>NE</RCSNbr>
                <VATNbr>12345613</VATNbr>
            </Agent>
            <Declarations>
                <Declarer>
                    <MatrNbr>12345678900</MatrNbr>
                    <RCSNbr>NE</RCSNbr>
                    <VATNbr>12345613</VATNbr>
                    <Declaration model="1" type="TVA_DECM" language="EN">
                        <Year>2019</Year>
                        <Period>11</Period>
                        <FormData>
                                <NumericField id="012">0,00</NumericField>
                                <NumericField id="014">0,00</NumericField>
                                <NumericField id="015">0,00</NumericField>
                                <NumericField id="016">0,00</NumericField>
                                <NumericField id="017">0,00</NumericField>
                                <NumericField id="018">0,00</NumericField>
                                <NumericField id="019">0,00</NumericField>
                                <NumericField id="021">0,00</NumericField>
                                <NumericField id="022">0,00</NumericField>
                                <NumericField id="031">0,00</NumericField>
                                <NumericField id="033">0,00</NumericField>
                                <NumericField id="037">0,00</NumericField>
                                <NumericField id="040">0,00</NumericField>
                                <NumericField id="046">0,00</NumericField>
                                <NumericField id="049">0,00</NumericField>
                                <NumericField id="051">0,00</NumericField>
                                <NumericField id="054">0,00</NumericField>
                                <NumericField id="056">0,00</NumericField>
                                <NumericField id="059">0,00</NumericField>
                                <NumericField id="063">0,00</NumericField>
                                <NumericField id="065">0,00</NumericField>
                                <NumericField id="068">0,00</NumericField>
                                <NumericField id="073">0,00</NumericField>
                                <NumericField id="076">0,00</NumericField>
                                <NumericField id="090">0,00</NumericField>
                                <NumericField id="092">0,00</NumericField>
                                <NumericField id="093">39,50</NumericField>
                                <NumericField id="094">0,00</NumericField>
                                <NumericField id="095">0,00</NumericField>
                                <NumericField id="096">0,00</NumericField>
                                <NumericField id="097">0,00</NumericField>
                                <NumericField id="102">39,50</NumericField>
                                <NumericField id="103">0,00</NumericField>
                                <NumericField id="104">39,50</NumericField>
                                <NumericField id="105">-39,50</NumericField>
                                <NumericField id="152">0,00</NumericField>
                                <NumericField id="194">0,00</NumericField>
                                <NumericField id="195">0,00</NumericField>
                                <NumericField id="196">0,00</NumericField>
                                <Choice id="204">0</Choice>
                                <Choice id="205">1</Choice>
                                <NumericField id="226">0,00</NumericField>
                                <NumericField id="227">0,00</NumericField>
                                <NumericField id="228">0,00</NumericField>
                                <NumericField id="403">0</NumericField>
                                <NumericField id="407">0,00</NumericField>
                                <NumericField id="409">0,00</NumericField>
                                <NumericField id="410">0,00</NumericField>
                                <NumericField id="418">0</NumericField>
                                <NumericField id="419">0,00</NumericField>
                                <NumericField id="423">0,00</NumericField>
                                <NumericField id="424">0,00</NumericField>
                                <NumericField id="431">0,00</NumericField>
                                <NumericField id="432">0,00</NumericField>
                                <NumericField id="435">0,00</NumericField>
                                <NumericField id="436">0,00</NumericField>
                                <NumericField id="441">0,00</NumericField>
                                <NumericField id="442">0,00</NumericField>
                                <NumericField id="445">0,00</NumericField>
                                <NumericField id="453">0</NumericField>
                                <NumericField id="454">0,00</NumericField>
                                <NumericField id="455">0,00</NumericField>
                                <NumericField id="456">0,00</NumericField>
                                <NumericField id="457">0,00</NumericField>
                                <NumericField id="458">39,50</NumericField>
                                <NumericField id="459">0,00</NumericField>
                                <NumericField id="460">0,00</NumericField>
                                <NumericField id="461">0,00</NumericField>
                                <NumericField id="462">0,00</NumericField>
                                <NumericField id="463">0,00</NumericField>
                                <NumericField id="464">0,00</NumericField>
                                <NumericField id="471">0,00</NumericField>
                                <NumericField id="472">0,00</NumericField>
                                <NumericField id="701">0,00</NumericField>
                                <NumericField id="702">0,00</NumericField>
                                <NumericField id="703">0,00</NumericField>
                                <NumericField id="704">0,00</NumericField>
                                <NumericField id="705">0,00</NumericField>
                                <NumericField id="706">0,00</NumericField>
                                <NumericField id="711">0,00</NumericField>
                                <NumericField id="712">0,00</NumericField>
                                <NumericField id="713">0,00</NumericField>
                                <NumericField id="714">0,00</NumericField>
                                <NumericField id="715">0,00</NumericField>
                                <NumericField id="716">0,00</NumericField>
                                <NumericField id="719">0,00</NumericField>
                                <NumericField id="721">0,00</NumericField>
                                <NumericField id="722">0,00</NumericField>
                                <NumericField id="723">0,00</NumericField>
                                <NumericField id="724">0,00</NumericField>
                                <NumericField id="725">0,00</NumericField>
                                <NumericField id="726">0,00</NumericField>
                                <NumericField id="729">0,00</NumericField>
                                <NumericField id="731">0,00</NumericField>
                                <NumericField id="732">0,00</NumericField>
                                <NumericField id="733">0,00</NumericField>
                                <NumericField id="734">0,00</NumericField>
                                <NumericField id="735">0,00</NumericField>
                                <NumericField id="736">0,00</NumericField>
                                <NumericField id="741">0,00</NumericField>
                                <NumericField id="742">0,00</NumericField>
                                <NumericField id="743">0,00</NumericField>
                                <NumericField id="744">0,00</NumericField>
                                <NumericField id="745">0,00</NumericField>
                                <NumericField id="746">0,00</NumericField>
                                <NumericField id="751">0,00</NumericField>
                                <NumericField id="752">0,00</NumericField>
                                <NumericField id="753">0,00</NumericField>
                                <NumericField id="754">0,00</NumericField>
                                <NumericField id="755">0,00</NumericField>
                                <NumericField id="756">0,00</NumericField>
                                <NumericField id="761">0,00</NumericField>
                                <NumericField id="762">0,00</NumericField>
                                <NumericField id="763">0,00</NumericField>
                                <NumericField id="764">0,00</NumericField>
                                <NumericField id="765">0,00</NumericField>
                                <NumericField id="766">0,00</NumericField>
                                <NumericField id="767">0,00</NumericField>
                                <NumericField id="768">0,00</NumericField>
                        </FormData>
                    </Declaration>
                </Declarer>
            </Declarations>
        </eCDFDeclarations>
        """ % options['filename']
        # Remove the <?xml version='1.0' encoding='UTF-8'?> from the string since the assert doesn't work with it
        xml = self.env[report.custom_handler_model_name].with_context(skip_xsd=True).export_tax_report_to_xml(options)['file_content'][38:]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml),
            self.get_xml_tree_from_string(expected_xml)
        )
