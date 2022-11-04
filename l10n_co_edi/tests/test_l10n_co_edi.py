# coding: utf-8

from .common import TestCoEdiCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestColombianInvoice(TestCoEdiCommon):

    def l10n_co_assert_generated_file_equal(self, invoice, expected_values, applied_xpath=None):
        # Get the file that we generate instead of the response from carvajal
        invoice.action_post()
        xml_content = self.edi_format._l10n_co_edi_generate_xml(invoice)
        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(expected_values)
        if applied_xpath:
            expected_etree = self.with_applied_xpath(expected_etree, applied_xpath)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice(self):
        '''Tests if we generate an accepted XML for an invoice and a credit note.'''
        with self.mock_carvajal():
            self.l10n_co_assert_generated_file_equal(self.invoice, self.expected_invoice_xml)

            # To stop a warning about "Tax Base Amount not computable
            # probably due to a change in an underlying tax " which seems
            # to be expected when generating refunds.
            with mute_logger('odoo.addons.account.models.account_invoice'):
                credit_note = self.invoice._reverse_moves(default_values_list=[])

            self.l10n_co_assert_generated_file_equal(credit_note, self.expected_credit_note_xml)

    def test_invoice_with_attachment_url(self):
        with self.mock_carvajal():
            self.invoice.l10n_co_edi_attachment_url = 'http://testing.te/test.zip'
            applied_xpath = '''
                <xpath expr="//ENC_16" position="after">
                    <ENC_17>http://testing.te/test.zip</ENC_17>
                </xpath>
            '''
            self.l10n_co_assert_generated_file_equal(self.invoice, self.expected_invoice_xml, applied_xpath)

    def test_invoice_carvajal_group_of_taxes(self):
        with self.mock_carvajal():
            self.invoice.write({
                'invoice_line_ids': [(1, self.invoice.invoice_line_ids.id, {
                    'tax_ids': [(6, 0, self.tax_group.ids)],
                    'name': 'Line 1',  # Otherwise it is recomputed
                })],
            })
            self.l10n_co_assert_generated_file_equal(self.invoice, self.expected_invoice_xml)
