# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_invoice_extract.models.account_invoice import SUCCESS
from odoo.addons.account_invoice_extract.tests import common as account_invoice_extract_common
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestInvoiceExtractPurchase(AccountTestInvoicingCommon, account_invoice_extract_common.MockIAP):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id |= cls.env.ref('base.group_system')

        # Required for `price_total` to be visible in the view
        config = cls.env['res.config.settings'].create({})
        config.show_line_subtotals_tax_selection = "tax_included"
        config.execute()

        # Avoid passing on the iap.account's `get` method to avoid the cr.commit breaking the test transaction.
        cls.env['iap.account'].create([
            {
                'service_name': 'partner_autocomplete',
                'company_ids': [(6, 0, cls.company_data['company'].ids)],
            },
            {
                'service_name': 'invoice_ocr',
                'company_ids': [(6, 0, cls.company_data['company'].ids)],
            },
        ])

        cls.vendor = cls.env['res.partner'].create({'name': 'Odoo', 'vat': 'BE0477472701'})
        cls.product1 = cls.env.ref('product.product_product_8')
        cls.product2 = cls.env.ref('product.product_product_9')
        cls.product3 = cls.env.ref('product.product_product_11')

        po = Form(cls.env['purchase.order'])
        po.partner_id = cls.vendor
        po.partner_ref = "INV1234"
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product1
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product2
            po_line.product_qty = 2
            po_line.price_unit = 50
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product3
            po_line.product_qty = 5
            po_line.price_unit = 20
        cls.purchase_order = po.save()
        cls.purchase_order.button_confirm()
        for line in cls.purchase_order.order_line:
            line.qty_received = line.product_qty

    def get_default_extract_response(self):
        return {
            'results': [{
                'supplier': {'selected_value': {'content': "Test"}, 'words': []},
                'total': {'selected_value': {'content': 300}, 'words': []},
                'subtotal': {'selected_value': {'content': 300}, 'words': []},
                'invoice_id': {'selected_value': {'content': 'INV0001'}, 'words': []},
                'currency': {'selected_value': {'content': 'EUR'}, 'words': []},
                'VAT_Number': {'selected_value': {'content': 'BE123456789'}, 'words': []},
                'date': {'selected_value': {'content': '2019-04-12 00:00:00'}, 'words': []},
                'due_date': {'selected_value': {'content': '2019-04-19 00:00:00'}, 'words': []},
                'global_taxes_amount': {'selected_value': {'content': 0.0}, 'words': []},
                'global_taxes': [{'selected_value': {'content': 0.0, 'amount_type': 'percent'}, 'words': []}],
                'email': {'selected_value': {'content': 'test@email.com'}, 'words': []},
                'website': {'selected_value': {'content': 'www.test.com'}, 'words': []},
                'payment_ref': {'selected_value': {'content': '+++123/1234/12345+++'}, 'words': []},
                'iban': {'selected_value': {'content': 'BE01234567890123'}, 'words': []},
                'purchase_order': {'selected_values': [{'content': "P12345"}], 'words': []},
                'invoice_lines': [
                    {
                        'description': {'selected_value': {'content': 'Test 1'}},
                        'unit_price': {'selected_value': {'content': 50}},
                        'quantity': {'selected_value': {'content': 1}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 50}},
                        'total': {'selected_value': {'content': 50}},
                    },
                    {
                        'description': {'selected_value': {'content': 'Test 2'}},
                        'unit_price': {'selected_value': {'content': 75}},
                        'quantity': {'selected_value': {'content': 2}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 150}},
                        'total': {'selected_value': {'content': 150}},
                    },
                    {
                        'description': {'selected_value': {'content': 'Test 3'}},
                        'unit_price': {'selected_value': {'content': 20}},
                        'quantity': {'selected_value': {'content': 5}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 100}},
                        'total': {'selected_value': {'content': 100}},
                    },
                ],
            }],
            'status_code': SUCCESS,
        }

    def test_match_po_by_name(self):
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_default_extract_response()
        extract_response['results'][0]['purchase_order']['selected_values'][0]['content'] = self.purchase_order.name

        with self.mock_iap_extract(extract_response, {}):
            invoice._check_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)

    def test_match_po_by_supplier_and_total(self):
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_default_extract_response()
        extract_response['results'][0]['supplier']['selected_value']['content'] = self.purchase_order.partner_id.name

        with self.mock_iap_extract(extract_response, {}):
            invoice._check_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)

    def test_match_subset_of_order_lines(self):
        # Test the case were only one subset of order lines match the total found by the OCR
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_default_extract_response()
        extract_response['results'][0]['purchase_order']['selected_values'][0]['content'] = self.purchase_order.name
        extract_response['results'][0]['total']['selected_value']['content'] = 200
        extract_response['results'][0]['subtotal']['selected_value']['content'] = 200
        extract_response['results'][0]['invoice_lines'] = extract_response['results'][0]['invoice_lines'][:2]

        with self.mock_iap_extract(extract_response, {}):
            invoice._check_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)
        self.assertEqual(invoice.amount_total, 200)

    def test_no_match_subset_of_order_lines(self):
        # Test the case were two subsets of order lines match the total found by the OCR
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_default_extract_response()
        extract_response['results'][0]['purchase_order']['selected_values'][0]['content'] = self.purchase_order.name
        extract_response['results'][0]['total']['selected_value']['content'] = 150
        extract_response['results'][0]['subtotal']['selected_value']['content'] = 150
        extract_response['results'][0]['invoice_lines'] = [extract_response['results'][0]['invoice_lines'][1]]

        with self.mock_iap_extract(extract_response, {}):
            invoice._check_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)
        # The PO should be used instead of the OCR result
        self.assertEqual(invoice.amount_total, 300)

    def test_no_match(self):
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_default_extract_response()

        with self.mock_iap_extract(extract_response, {}):
            invoice._check_status()

        self.assertTrue(invoice.id not in self.purchase_order.invoice_ids.ids)
