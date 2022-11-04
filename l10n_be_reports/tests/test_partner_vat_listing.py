# -*- coding: utf-8 -*-
# pylint: disable=C0326
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class BelgiumPartnerVatListingTest(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_a_be = cls.env['res.partner'].create({
            'name': 'Partner A (BE)',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0246697724',
        })

        cls.partner_b_be = cls.env['res.partner'].create({
            'name': 'Partner B (BE)',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0766998497',
        })

        cls.report = cls.env.ref('l10n_be_reports.l10n_be_partner_vat_listing')

    @classmethod
    def create_and_post_account_move(cls, move_type, partner_id, invoice_date, product_quantity, product_price_unit):
        move = cls.env['account.move'].create({
            'move_type': move_type,
            'partner_id': partner_id,
            'invoice_date': invoice_date,
            'date': fields.Date.from_string(invoice_date),
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'quantity': product_quantity,
                'name': 'Product 1',
                'price_unit': product_price_unit,
                'tax_ids': cls.tax_sale_a.ids,
            })]
        })

        move.action_post()

    def test_simple_invoice(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        # Foreign partners invoices should not show
        self.create_and_post_account_move('out_invoice', self.partner_a.id, '2022-06-01', product_quantity=100, product_price_unit=50)

        # Belgian partners with out-of-date range invoices should not be shown
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-07-01', product_quantity=10, product_price_unit=200)

        # Invoices from Belgian partners should show up ordered by vat number
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=100)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 3000.0,             630.0),
                ('Partner A (BE)',          'BE0246697724',     1000.0,             210.0),
                ('Partner B (BE)',          'BE0766998497',     2000.0,             420.0),
            ],
        )

    def test_invoices_with_refunds(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        # Partial refund
        self.create_and_post_account_move('out_invoice', self.partner_a_be.id, '2022-06-01', product_quantity=10, product_price_unit=100)
        self.create_and_post_account_move('out_refund', self.partner_a_be.id, '2022-06-02', product_quantity=2, product_price_unit=100)

        # Full refund
        self.create_and_post_account_move('out_invoice', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)
        self.create_and_post_account_move('out_refund', self.partner_b_be.id, '2022-06-01', product_quantity=10, product_price_unit=200)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 800.0,              168.0),
                ('Partner A (BE)',          'BE0246697724',     800.0,              168.0),
                ('Partner B (BE)',          'BE0766998497',     0.0,                0.0),
            ],
        )

    def test_refunds_without_invoices(self):
        self.env.companies = self.env.company
        options = self._generate_options(self.report, fields.Date.from_string('2022-06-01'), fields.Date.from_string('2022-06-30'))

        self.create_and_post_account_move('out_refund', self.partner_a_be.id, '2022-06-02', product_quantity=10, product_price_unit=100)

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                        VAT number          Turnover            VAT amount
            [   0,                          1,                  2,                  3],
            [
                ('Partner VAT Listing',     '',                 -1000.0,            -210.0),
                ('Partner A (BE)',          'BE0246697724',     -1000.0,            -210.0),
            ],
        )
