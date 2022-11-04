# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class OSSTaxReportTest(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.company.account_fiscal_country_id = cls.env.ref('base.be')
        cls.env.company.vat = 'BE0477472701'

        tax_21 = cls.env['account.tax'].create({
            'name': "tax_21",
            'amount_type': 'percent',
            'amount': 21.0,
            'country_id': cls.env.ref('base.be').id
        })

        cls.env.company._map_eu_taxes()

        cls.product_1 = cls.env['product.product'].create({
            'name': 'product_1',
            'lst_price': 1000.0,
            'taxes_id': [Command.set(tax_21.ids)],
        })

        cls.partner_be = cls.env['res.partner'].create({
            'name': 'Partner BE',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.partner_fr = cls.env['res.partner'].create({
            'name': 'Partner FR',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.partner_lu = cls.env['res.partner'].create({
            'name': 'Partner LU',
            'country_id': cls.env.ref('base.lu').id,
        })

        cls.init_invoice('out_invoice', partner=cls.partner_be, products=cls.product_1, invoice_date=fields.Date.from_string('2021-04-01'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_fr, products=cls.product_1, invoice_date=fields.Date.from_string('2021-05-23'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_lu, products=cls.product_1, invoice_date=fields.Date.from_string('2021-06-12'), post=True)

    def test_tax_report_oss(self):
        """ Test tax report's content for 'domestic' foreign VAT fiscal position option.
        """
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, fields.Date.from_string('2021-04-01'), fields.Date.from_string('2021-06-30'))

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                        Net               Tax
            [   0,                            1,                2],
            [
                ("Sales",                    '',              370),
                ("France",                   '',              200),
                ("20.0% FR VAT (20.0%)",   1000,              200),
                ("Total France",             '',              200),
                ("Luxembourg",               '',              170),
                ("17.0% LU VAT (17.0%)",   1000,              170),
                ("Total Luxembourg",         '',              170),
                ("Total Sales",              '',              370),
            ],
        )

    def test_generate_oss_xml_be(self):
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, fields.Date.from_string('2021-04-01'), fields.Date.from_string('2021-06-30'))

        expected_xml = """
            <ns0:OSSConsignment
              xmlns:ns2="urn:minfin.fgov.be:oss:common"
              xmlns:ns1="http://www.minfin.fgov.be/InputCommon"
              xmlns:ns0="http://www.minfin.fgov.be/OSSDeclaration"
              OSSDeclarationNbr="1">
              <ns0:OSSDeclaration SequenceNumber="1">
                <ns0:Trader_ID>
                  <ns2:VATNumber issuedBy="BE">0477472701</ns2:VATNumber>
                </ns0:Trader_ID>
                <ns0:Period>
                  <ns2:Year>2021</ns2:Year>
                  <ns2:Quarter>2</ns2:Quarter>
                </ns0:Period>
                <ns0:OSSDeclarationInfo SequenceNumber="1">
                  <ns2:MemberStateOfConsumption>FR</ns2:MemberStateOfConsumption>
                  <ns2:OSSDeclarationRows SequenceNumber="1">
                    <ns2:SupplyType>GOODS</ns2:SupplyType>
                    <ns2:FixedEstablishment>
                        <ns2:VATIdentificationNumber issuedBy="BE">0477472701</ns2:VATIdentificationNumber>
                    </ns2:FixedEstablishment>
                    <ns2:VatRateType>20.0</ns2:VatRateType>
                    <ns2:VatAmount currency="USD">200.0</ns2:VatAmount>
                    <ns2:TaxableAmount currency="USD">1000.0</ns2:TaxableAmount>
                  </ns2:OSSDeclarationRows>
                  <ns2:CorrectionsInfo>
                  </ns2:CorrectionsInfo>
                </ns0:OSSDeclarationInfo>
                <ns0:OSSDeclarationInfo SequenceNumber="2">
                  <ns2:MemberStateOfConsumption>LU</ns2:MemberStateOfConsumption>
                  <ns2:OSSDeclarationRows SequenceNumber="1">
                    <ns2:SupplyType>GOODS</ns2:SupplyType>
                    <ns2:FixedEstablishment>
                        <ns2:VATIdentificationNumber issuedBy="BE">0477472701</ns2:VATIdentificationNumber>
                    </ns2:FixedEstablishment>
                    <ns2:VatRateType>17.0</ns2:VatRateType>
                    <ns2:VatAmount currency="USD">170.0</ns2:VatAmount>
                    <ns2:TaxableAmount currency="USD">1000.0</ns2:TaxableAmount>
                  </ns2:OSSDeclarationRows>
                  <ns2:CorrectionsInfo>
                  </ns2:CorrectionsInfo>
                </ns0:OSSDeclarationInfo>
              </ns0:OSSDeclaration>
            </ns0:OSSConsignment>
        """

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTaxReportOSSNoMapping(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].account_fiscal_country_id = cls.env.ref('base.be')
        cls.company_data['company'].vat = 'BE0477472701'

        cls.tax_report = cls.env['account.report'].create({
            'name': 'Fictive tax report',
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
            'root_report_id': cls.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance',})],
        })
        report_line_invoice_base_line = cls._create_tax_report_line('Invoice base', cls.tax_report, sequence=1, tag_name='invoice_base_line')
        report_line_refund_base_line = cls._create_tax_report_line('Refund base', cls.tax_report, sequence=2, tag_name='refund_base_line')

        # Create an OSS tax from scratch
        oss_tag = cls.env.ref('l10n_eu_oss.tag_oss')
        cls.oss_tax = cls.env['account.tax'].create({
            'name': 'OSS tax for DK',
            'amount': 25,
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(report_line_invoice_base_line.expression_ids._get_matching_tags().filtered(lambda x: not x.tax_negate).ids + oss_tag.ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(oss_tag.ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(report_line_refund_base_line.expression_ids._get_matching_tags().filtered(lambda x: not x.tax_negate).ids + oss_tag.ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(oss_tag.ids)],
                }),
            ],
        })

        cls.env['account.fiscal.position'].create({
            'name': 'OSS B2C Denmark',
            'country_id': cls.env.ref('base.dk').id,
            'company_id': cls.company_data['company'].id,
            'auto_apply': True,
            'tax_ids': [Command.create({'tax_src_id': cls.tax_sale_a.id, 'tax_dest_id': cls.oss_tax.id})],
        })


    def test_oss_tax_report_mixed_tags(self):
        """Checks that the tax report correctly takes into account the amount of the account move lines wearing tax tag
        when it is also wearing an OSS tag.
        """
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2022-02-01'),
            amounts=[100.0],
            taxes=[self.oss_tax],
            post=True,
        )
        options = self._generate_options(
            self.tax_report,
            fields.Date.from_string('2022-02-01'),
            fields.Date.from_string('2022-02-28'),
        )
        report_results = self.tax_report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=C0326
            report_results,
            #   Name             Balance
            [   0,                    1],
            [
                ('Invoice base', 100.00),
                ('Refund base',      ''),
            ],
        )

    def test_closing_entry(self):
        """Check the closing entry doesn't take the account move line wearing the OSS tag into account"""
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2022-02-01'),
            amounts=[100.0],
            taxes=[self.oss_tax],
            post=True,
        )
        options = self._generate_options(
            self.tax_report,
            fields.Date.from_string('2022-02-01'),
            fields.Date.from_string('2022-02-28'),
        )
        tax_closing_entry_lines = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(self.tax_report, options).line_ids.filtered(lambda l: l.balance != 0.0)

        self.assertEqual(len(tax_closing_entry_lines), 0, "The tax closing entry shouldn't take amls wearing the OSS tag into account")

    def test_tax_report_oss(self):
        """ Test tax report's content for 'domestic' foreign VAT fiscal position option."""
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2022-02-01'),
            amounts=[100.0],
            taxes=[self.oss_tax],
            post=True,
        )
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, '2022-02-01', '2022-02-28')
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                          Net               Tax
            [   0,                              1,                2],
            [
                ("Sales",                      '',             25.0),
                ("Denmark",                    '',             25.0),
                ("OSS tax for DK (25.0%)",  100.0,             25.0),
                ("Total Denmark",              '',             25.0),
                ("Total Sales",                '',             25.0),
            ],
        )
