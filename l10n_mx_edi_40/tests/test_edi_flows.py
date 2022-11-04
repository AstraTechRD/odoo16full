# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon, mocked_l10n_mx_edi_pac
from odoo.addons.account_edi.tests.common import _mocked_cancel_success

from odoo.tests import tagged
from odoo.exceptions import UserError

from freezegun import freeze_time
from unittest.mock import patch


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFlows(TestMxEdiCommon):

    def test_invoice_flow_not_sent(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac):
            self.invoice.action_post()

            document = self.invoice.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertEqual(len(document), 1)

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self.invoice.button_draft()

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self.invoice.button_cancel()

            self.assertRecordValues(self.invoice, [{'edi_state': 'cancelled'}])
            self.assertRecordValues(document, [{'state': 'cancelled'}])
            self.assertFalse(document.attachment_id)

    def test_invoice_flow_sent_twice(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_cancel_invoice',
                   new=_mocked_cancel_success):
            self.invoice.action_post()

            document = self.invoice.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertEqual(len(document), 1)

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(self.invoice, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            with self.assertRaises(UserError), self.cr.savepoint():
                self.invoice.button_draft()
            self.invoice.button_cancel_posted_moves()

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_cancel'}])
            self.assertRecordValues(document, [{'state': 'to_cancel'}])
            self.assertTrue(document.attachment_id)

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(self.invoice, [{'edi_state': 'cancelled'}])
            self.assertRecordValues(document, [{'state': 'cancelled'}])
            self.assertFalse(document.attachment_id)

            self.invoice.button_draft()

            self.assertRecordValues(self.invoice, [{'edi_state': 'cancelled'}])
            self.assertRecordValues(document, [{'state': 'cancelled'}])

            self.invoice.action_post()

            self.assertRecordValues(self.invoice, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(self.invoice, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

    def test_payment_flow_PUE_invoice(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):
            self.payment.action_post()

            self.assertFalse(self.payment.edi_document_ids)

            self.invoice.action_post()

            move = self.payment.move_id

            self.assertRecordValues(move, [{'edi_state': False}])
            self.assertFalse(move.edi_document_ids)

            # Invoice is using a 'PUE' payment policy. Sending the payment to the government is not mandatory by
            # default.
            (self.invoice + self.payment.move_id).line_ids\
                .filtered(lambda line: line.account_type == 'asset_receivable')\
                .reconcile()

            self.assertRecordValues(move, [{'edi_state': False}])
            self.assertFalse(move.edi_document_ids)

            self.payment.action_l10n_mx_edi_force_generate_cfdi()

            document = self.payment.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertEqual(len(document), 1)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

    def test_payment_flow_PPD_invoice(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):
            # Set the payment method of invoice to PPD.
            self.payment.action_post()

            self.assertFalse(self.payment.edi_document_ids)

            self.invoice.action_post()

            move = self.payment.move_id

            self.assertRecordValues(move, [{'edi_state': False}])
            self.assertFalse(move.edi_document_ids)

            # Invoice is using a 'PPD' payment policy. Sending the payment to the government is mandatory.
            self.invoice.invoice_date_due = '2018-01-01'
            (self.invoice + self.payment.move_id).line_ids\
                .filtered(lambda line: line.account_type == 'asset_receivable')\
                .reconcile()

            document = self.payment.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertEqual(len(document), 1)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

    def test_payment_flow_unreconcile(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_cancel_payment',
                   new=_mocked_cancel_success):
            self.payment.action_post()
            self.invoice.action_post()

            (self.invoice + self.payment.move_id).line_ids\
                .filtered(lambda line: line.account_type == 'asset_receivable')\
                .reconcile()

            move = self.payment.move_id

            self.payment.action_l10n_mx_edi_force_generate_cfdi()
            self._process_documents_web_services(self.invoice)
            self._process_documents_web_services(move)

            document = self.payment.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            move.line_ids.remove_move_reconcile()

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])
            self.assertTrue(document.attachment_id)

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            self.payment.action_draft()

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            self.payment.action_cancel()

            self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])
            self.assertRecordValues(document, [{'state': 'to_cancel'}])
            self.assertTrue(document.attachment_id)

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'cancelled'}])
            self.assertRecordValues(document, [{'state': 'cancelled'}])
            self.assertFalse(document.attachment_id)

    def test_payment_flow_cancel_reconciled_invoice(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_cancel_invoice',
                   new=_mocked_cancel_success), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_cancel_payment',
                   new=_mocked_cancel_success):
            self.payment.action_post()
            self.invoice.action_post()

            (self.invoice + self.payment.move_id).line_ids\
                .filtered(lambda line: line.account_type == 'asset_receivable')\
                .reconcile()

            move = self.payment.move_id

            self.payment.action_l10n_mx_edi_force_generate_cfdi()
            self._process_documents_web_services(self.invoice)
            self._process_documents_web_services(move)

            document = self.payment.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            self.invoice.button_cancel_posted_moves()

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])
            self.assertTrue(document.attachment_id)

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            self.payment.action_draft()

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)

            self.payment.action_cancel()

            self.assertRecordValues(move, [{'edi_state': 'to_cancel'}])
            self.assertRecordValues(document, [{'state': 'to_cancel'}])
            self.assertTrue(document.attachment_id)

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'cancelled'}])
            self.assertRecordValues(document, [{'state': 'cancelled'}])
            self.assertFalse(document.attachment_id)

    def test_statement_flow_PUE_invoice(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_invoice_pac',
                   new=mocked_l10n_mx_edi_pac), \
             patch('odoo.addons.l10n_mx_edi.models.account_edi_format.AccountEdiFormat._l10n_mx_edi_post_payment_pac',
                   new=mocked_l10n_mx_edi_pac):

            self.assertFalse(self.statement_line.edi_document_ids)

            self.invoice.action_post()

            move = self.statement_line.move_id

            self.assertRecordValues(move, [{'edi_state': False}])
            self.assertFalse(move.edi_document_ids)

            # Invoice is using a 'PUE' payment policy. Sending the payment to the government is not mandatory by
            # default.
            # Reconcile without the bank reconciliation widget since the widget is in account_accountant.
            # bank rec widget only in account_accountant
            receivable_line = self.invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
            dummy, st_suspense_lines, _st_other_lines = self.statement_line \
                .with_context(skip_account_move_synchronization=True) \
                ._seek_for_lines()
            st_suspense_lines.account_id = receivable_line.account_id
            (st_suspense_lines + receivable_line).reconcile()

            self.assertRecordValues(move, [{'edi_state': False}])
            self.assertFalse(move.edi_document_ids)

            self.statement_line.action_l10n_mx_edi_force_generate_cfdi()

            document = self.statement_line.edi_document_ids.filtered(lambda d: d.edi_format_id == self.env.ref('l10n_mx_edi.edi_cfdi_3_3'))

            self.assertEqual(len(document), 1)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(self.invoice)

            self.assertRecordValues(move, [{'edi_state': 'to_send'}])
            self.assertRecordValues(document, [{'state': 'to_send'}])

            self._process_documents_web_services(move)

            self.assertRecordValues(move, [{'edi_state': 'sent'}])
            self.assertRecordValues(document, [{'state': 'sent'}])
            self.assertTrue(document.attachment_id)
