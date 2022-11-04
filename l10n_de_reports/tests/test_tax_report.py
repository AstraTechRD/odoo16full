# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class GermanTaxReportTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_de_skr03.l10n_de_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.de').id,
            'vat': 'DE123456788',
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @freeze_time('2019-12-31')
    def test_generate_xml(self):
        first_tax = self.env['account.tax'].search([('name', '=', '19% Umsatzsteuer'), ('company_id', '=', self.company_data['company'].id)], limit=1)
        second_tax = self.env['account.tax'].search([('name', '=', 'Innergem. Erwerb 19%USt/19%VSt'), ('company_id', '=', self.company_data['company'].id)], limit=1)

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
                'price_unit': 75,
                'tax_ids': second_tax.ids,
            })]
        })
        move.action_post()

        report = self.env.ref('l10n_de.tax_report')
        options = report._get_options()

        expected_xml = """
        <Anmeldungssteuern art="UStVA" version="201801">
            <DatenLieferant>
                <Name>company_1_data</Name>
                <Strasse />
                <PLZ />
                <Ort />
                <Telefon>+32475123456</Telefon>
                <Email>jsmith@mail.com</Email>
            </DatenLieferant>
            <Erstellungsdatum>20191231</Erstellungsdatum>
            <Steuerfall>
                <Umsatzsteuervoranmeldung>
                    <Jahr>2019</Jahr>
                    <Zeitraum>11</Zeitraum>
                    <Steuernummer />
                    <Kz09>0.00</Kz09>
                    <Kz81>28</Kz81>
                    <Kz89>14</Kz89>
                    <Kz61>-14</Kz61>
                    <Kz83>0.00</Kz83>
                </Umsatzsteuervoranmeldung>
            </Steuerfall>
        </Anmeldungssteuern>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].export_tax_report_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )
