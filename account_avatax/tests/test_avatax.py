from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.modules.neutralize import get_neutralization_queries
from .common import TestAccountAvataxCommon


@tagged("-at_install", "post_install")
class TestAccountAvalaraInternal(TestAccountAvataxCommon):
    def assertInvoice(self, invoice, test_exact_response):
        self.assertEqual(
            len(invoice.invoice_line_ids.tax_ids),
            0,
            "There should be no tax rate on the line."
        )

        self.assertRecordValues(invoice, [{
            'amount_total': 90.0,
            'amount_untaxed': 90.0,
            'amount_tax': 0.0,
        }])
        invoice.action_post()

        if test_exact_response:
            self.assertRecordValues(invoice, [{
                'amount_total': 96.54,
                'amount_untaxed': 90.0,
                'amount_tax': 6.54,
            }])

            avatax_mapping = {avatax_line['lineNumber']: avatax_line for avatax_line in test_exact_response['lines']}
            for line in invoice.invoice_line_ids:
                line_number = f'account.move.line,{line.id}'
                self.assertIn(line_number, avatax_mapping)
                avatax_line = avatax_mapping[line_number]
                self.assertEqual(
                    line.price_total,
                    avatax_line['tax'] + avatax_line['lineAmount'],
                    f"Tax-included price doesn't match tax returned by Avatax for line {line.id} (product: {line.product_id.display_name})."
                )
                self.assertEqual(
                    line.price_subtotal,
                    avatax_line['lineAmount'],
                    f"Wrong Avatax amount for {line.id} (product: {line.product_id.display_name}), there is probably a mismatch between the test SO and the mocked response."
                )

        else:
            for line in invoice.invoice_line_ids:
                product_name = line.product_id.display_name
                self.assertGreater(len(line.tax_ids), 0, "Line with %s did not get any taxes set." % product_name)

            self.assertGreater(invoice.amount_tax, 0.0, "Invoice has a tax_amount of 0.0.")

    def test_01_odoo_invoice(self):
        invoice, response = self._create_invoice_01_and_expected_response()
        with self._capture_request(return_value=response):
            self.assertInvoice(invoice, test_exact_response=response)

        # verify transactions are uncommitted
        with patch('odoo.addons.account_avatax.models.account_avatax.AccountAvatax._uncommit_avatax_transaction') as mocked_commit:
            invoice.button_draft()
            mocked_commit.assert_called()

    def test_integration_01_odoo_invoice(self):
        with self._skip_no_credentials():
            invoice, _ = self._create_invoice_01_and_expected_response()
            self.assertInvoice(invoice, test_exact_response=False)
            invoice.button_draft()

    def test_02_odoo_invoice(self):
        invoice, response = self._create_invoice_02_and_expected_response()
        with self._capture_request(return_value=response):
            self.assertInvoice(invoice, test_exact_response=response)

        # verify transactions are uncommitted
        with patch('odoo.addons.account_avatax.models.account_avatax.AccountAvatax._uncommit_avatax_transaction') as mocked_commit:
            invoice.button_draft()
            mocked_commit.assert_called()

    def test_integration_02_odoo_invoice(self):
        with self._skip_no_credentials():
            invoice, _ = self._create_invoice_02_and_expected_response()
            self.assertInvoice(invoice, test_exact_response=False)
            invoice.button_draft()

    def test_01_odoo_refund(self):
        invoice, response = self._create_invoice_01_and_expected_response()

        with self._capture_request(return_value=response):
            invoice.action_post()

        move_reversal = self.env['account.move.reversal'] \
            .with_context(active_model='account.move', active_ids=invoice.ids) \
            .create({'refund_method': 'refund', 'journal_id': invoice.journal_id.id})
        refund = self.env['account.move'].browse(move_reversal.reverse_moves()['res_id'])

        # Amounts should be sent as negative for refunds:
        # https://developer.avalara.com/erp-integration-guide/sales-tax-badge/transactions/test-refunds/
        for line in refund._get_avatax_invoice_lines():
            if 'Discount' in line['description']:
                self.assertGreater(line['amount'], 0)
            else:
                self.assertLess(line['amount'], 0)

    def test_unlink(self):
        invoice, _ = self._create_invoice_01_and_expected_response()

        mock_response = {'error': {'code': 'EntityNotFoundError',
           'details': [{'code': 'EntityNotFoundError',
                        'description': "The Document with code 'Journal Entry "
                                       "2180' was not found.",
                        'faultCode': 'Client',
                        'helpLink': 'http://developer.avalara.com/avatax/errors/EntityNotFoundError',
                        'message': 'Document not found.',
                        'number': 4,
                        'severity': 'Error'}],
           'message': 'Document not found.',
           'target': 'HttpRequest'}}

        with self._capture_request(return_value=mock_response) as capture:
            invoice.unlink()

        self.assertEqual(capture.val['json']['code'], 'DocVoided', 'Should have tried to void without raising on EntityNotFoundError.')

    def test_journal_entry(self):
        entry, _ = self._create_invoice_01_and_expected_response()
        entry.move_type = 'entry'

        with self._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            entry.action_post()

        self.assertIsNone(capture.val, "Journal entries should not be sent to Avatax.")

    def test_invoice_multi_company(self):
        invoice, response = self._create_invoice_01_and_expected_response()

        company_2 = self.company_data_2['company']
        company_2.account_fiscal_country_id = self.env.ref('base.be')
        self.env.user.company_id = company_2
        with self._capture_request(return_value=response):
            # ensure this doesn't raise:
            # odoo.exceptions.ValidationError
            # This entry contains some tax from an unallowed country. Please check its fiscal position and your tax configuration.
            invoice.button_update_avatax()


@tagged("-at_install", "post_install")
class TestAccountAvalaraSalesTaxAdministration(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/sales-tax-badge/"""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)
        cls.config = cls.env['res.config.settings'].create({})
        return res

    def test_disable_document_recording(self):
        """In order for this connector to be used in conjunction with other integrations to AvaTax,
        the user must be able to control which connector is used for recording documents to AvaTax.

        From a technical standpoint, simply use DocType: 'SalesOrder' on all calls
        and suppress any non-getTax calls (i.e. cancelTax, postTax).
        """
        self.env.company.avalara_commit = False
        invoice, response = self._create_invoice_01_and_expected_response()
        with self._capture_request(return_value=response), patch('odoo.addons.account_avatax.lib.avatax_client.AvataxClient.commit_transaction') as mocked_commit:
            invoice.action_post()
            mocked_commit.assert_not_called()

    def test_disable_avatax(self):
        """The user must have an option to turn on or off the AvaTax Calculation service
        independent of any other Avalara product or service.
        """
        self.fp_avatax.is_avatax = False
        with patch('odoo.addons.account_avatax.lib.avatax_client.AvataxClient.request') as mocked_request:
            self._create_invoice()
            mocked_request.assert_not_called()

    def test_disable_avatax_neutralize(self):
        """ORM's neutralization feature works."""
        self.cr.execute(next(get_neutralization_queries(['account_avatax'])))
        with patch('odoo.addons.account_avatax.lib.avatax_client.AvataxClient.request') as mocked_request:
            self._create_invoice()
            mocked_request.assert_not_called()

    def test_integration_connect_button(self):
        """Test the connection to the AvaTax service and verify the AvaTax credentials."""
        with self._skip_no_credentials(), self.assertRaisesRegex(UserError, "'version'"):
            self.config.avatax_ping()
