# -*- coding: utf-8 -*-
from unittest.mock import patch

from .common import TestL10nClEdiCommon, _check_with_xsd_patch
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10AccountMoveReversal(TestL10nClEdiCommon):
    @classmethod
    @patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
    def setUpClass(cls, chart_template_ref='l10n_cl.cl_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': cls.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-23',
            'currency_id': cls.env.ref('base.CLP').id,
            'journal_id': cls.sale_journal.id,
            'l10n_latam_document_type_id': cls.env.ref('l10n_cl.dc_y_f_dte').id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'quantity': 2,
                'price_unit': 100000.0,
                'tax_ids': [],
            }), (0, 0, {
                'name': 'Desk Combination',
                'product_id': cls.product_a.id,
                'quantity': 2,
                'price_unit': 2400000.0,
                'tax_ids': [],
            })],
        })
        cls.invoice.with_context(skip_xsd=True).action_post()

    def test_l10n_cl_account_move_reversal_partial_refund(self):
        # Corrects Referenced Document Amount
        refund_wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
            'reason': 'Test Partial Refund',
            'refund_method': 'refund',
            'journal_id': self.invoice.journal_id.id,
        })
        res = refund_wizard.reverse_moves()
        refund = self.env['account.move'].browse(res['res_id'])

        self.assertEqual(len(refund), 1)
        self.assertEqual(refund.state, 'draft')
        self.assertEqual(refund.ref, 'Reversal of: %s, %s' % (self.invoice.name, refund_wizard.reason))
        self.assertEqual(refund.invoice_line_ids.mapped('name'), self.invoice.invoice_line_ids.mapped('name'))

        # Corrects Referenced Document Text
        refund_wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=self.invoice.ids).create({
                'reason': 'Test Partial Refund',
                'refund_method': 'refund',
                'l10n_cl_is_text_correction': True,
                'l10n_cl_edi_reference_doc_code': '2',
                'l10n_cl_original_text': 'Test Original Text',
                'l10n_cl_corrected_text': 'Test Corrected Text',
                'journal_id': self.invoice.journal_id.id,
            })
        res = refund_wizard.reverse_moves()
        refund = self.env['account.move'].browse(res['res_id'])

        self.assertEqual(len(refund.invoice_line_ids), 1)
        self.assertEqual(refund.invoice_line_ids.name, 'Where it says: Test Original Text should say: Test Corrected Text')
        self.assertEqual(refund.invoice_line_ids.quantity, 1.0)
        self.assertEqual(refund.invoice_line_ids.price_unit, 0)
        self.assertEqual(refund.invoice_line_ids.price_subtotal, 0)
