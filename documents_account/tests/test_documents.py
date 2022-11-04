# -*- coding: utf-8 -*-

import base64
from odoo.tests.common import tagged, TransactionCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("workflow bridge account", 'utf-8'))


@tagged('post_install', '-at_install', 'test_document_bridge')
class TestCaseDocumentsBridgeAccount(TransactionCase):

    def setUp(self):
        super(TestCaseDocumentsBridgeAccount, self).setUp()
        self.folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
        })
        self.folder_a_a = self.env['documents.folder'].create({
            'name': 'folder A - A',
            'parent_folder_id': self.folder_a.id,
        })
        self.document_txt = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
        })
        self.document_gif = self.env['documents.document'].create({
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_a.id,
        })

        self.workflow_rule_vendor_bill = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule create vendor bill on f_a',
            'create_model': 'account.move.in_invoice',
        })

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (vendor bill & credit note).

        """
        self.assertEqual(self.document_txt.res_model, 'documents.document', "failed at default res model")
        multi_return = self.workflow_rule_vendor_bill.apply_actions([self.document_txt.id, self.document_gif.id])
        self.assertEqual(multi_return.get('type'), 'ir.actions.act_window',
                         'failed at invoice workflow return value type')
        self.assertEqual(multi_return.get('res_model'), 'account.move',
                         'failed at invoice workflow return value res model')

        self.assertEqual(self.document_txt.res_model, 'account.move', "failed at workflow_bridge_dms_account"
                                                                           " new res_model")
        vendor_bill_txt = self.env['account.move'].search([('id', '=', self.document_txt.res_id)])
        self.assertTrue(vendor_bill_txt.exists(), 'failed at workflow_bridge_dms_account vendor_bill')
        self.assertEqual(self.document_txt.res_id, vendor_bill_txt.id, "failed at workflow_bridge_dms_account res_id")
        self.assertEqual(vendor_bill_txt.move_type, 'in_invoice', "failed at workflow_bridge_dms_account vendor_bill type")
        vendor_bill_gif = self.env['account.move'].search([('id', '=', self.document_gif.res_id)])
        self.assertEqual(self.document_gif.res_id, vendor_bill_gif.id, "failed at workflow_bridge_dms_account res_id")

        single_return = self.workflow_rule_vendor_bill.apply_actions([self.document_txt.id])
        self.assertEqual(single_return.get('res_model'), 'account.move',
                         'failed at invoice res_model action from workflow create model')
        invoice = self.env[single_return['res_model']].browse(single_return.get('res_id'))
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', invoice.id)])
        self.assertEqual(len(attachments), 1, 'there should only be one ir attachment matching')

    def test_bridge_account_account_settings_on_write(self):
        """
        Makes sure the settings apply their values when an ir_attachment is set as message_main_attachment_id
        on invoices.
        """
        folder_test = self.env['documents.folder'].create({'name': 'folder_test'})
        self.env.user.company_id.documents_account_settings = True

        for invoice_type in ['in_invoice', 'out_invoice', 'in_refund', 'out_refund']:
            invoice_test = self.env['account.move'].with_context(default_move_type=invoice_type).create({
                'name': 'invoice_test',
                'move_type': invoice_type,
            })
            setting = self.env['documents.account.folder.setting'].create({
                'folder_id': folder_test.id,
                'journal_id': invoice_test.journal_id.id,
            })
            attachment_txt_test = self.env['ir.attachment'].create({
                'datas': TEXT,
                'name': 'fileText_test.txt',
                'mimetype': 'text/plain',
                'res_model': 'account.move',
                'res_id': invoice_test.id
            })
            attachment_txt_alternative_test = self.env['ir.attachment'].create({
                'datas': TEXT,
                'name': 'fileText_test_alternative.txt',
                'mimetype': 'text/plain',
                'res_model': 'account.move',
                'res_id': invoice_test.id
            })
            attachment_txt_main_attachment_test = self.env['ir.attachment'].create({
                'datas': TEXT,
                'name': 'fileText_main_attachment.txt',
                'mimetype': 'text/plain',
                'res_model': 'account.move',
                'res_id': invoice_test.id
            })

            invoice_test.write({'message_main_attachment_id': attachment_txt_test.id})
            txt_doc = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
            self.assertEqual(txt_doc.folder_id, folder_test, 'the text test document have a folder')
            invoice_test.write({'message_main_attachment_id': attachment_txt_alternative_test.id})
            self.assertEqual(txt_doc.attachment_id.id, attachment_txt_alternative_test.id,
                             "the attachment of the document should have swapped")
            attachment_txt_main_attachment_test.register_as_main_attachment()
            self.assertEqual(txt_doc.attachment_id.id, attachment_txt_main_attachment_test.id,
                             "the attachment of the document should have swapped")
            # deleting the setting to prevent duplicate settings.
            setting.unlink()

    def test_journal_entry(self):
        """
        Makes sure the settings apply their values when an ir_attachment is set as message_main_attachment_id
        on invoices.
        """
        folder_test = self.env['documents.folder'].create({'name': 'Bills'})
        self.env.user.company_id.documents_account_settings = True

        invoice_test = self.env['account.move'].with_context(default_move_type='entry').create({
            'name': 'Journal Entry',
            'move_type': 'entry',
        })
        setting = self.env['documents.account.folder.setting'].create({
            'folder_id': folder_test.id,
            'journal_id': invoice_test.journal_id.id,
        })
        attachments = self.env['ir.attachment'].create([{
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'account.move',
            'res_id': invoice_test.id
        }, {
            'datas': TEXT,
            'name': 'fileText_test2.txt',
            'mimetype': 'text/plain',
            'res_model': 'account.move',
            'res_id': invoice_test.id
        }])
        documents = self.env['documents.document'].search([('attachment_id', 'in', attachments.ids)])
        self.assertEqual(len(documents), 2)
        setting.unlink()

    def test_bridge_account_workflow_settings_on_write(self):
        """
        Tests that tags added by a workflow action are not completely overridden by the settings.
        """
        self.env.user.company_id.documents_account_settings = True
        tag_category_a = self.env['documents.facet'].create({
            'folder_id': self.folder_a.id,
            'name': "categ_a",
        })
        tag_a = self.env['documents.tag'].create({
            'facet_id': tag_category_a.id,
            'name': "tag_a",
        })
        tag_b = self.env['documents.tag'].create({
            'facet_id': tag_category_a.id,
            'name': "tag_b",
        })
        tag_action_a = self.env['documents.workflow.action'].create({
            'action': 'add',
            'facet_id': tag_category_a.id,
            'tag_id': tag_a.id,
        })
        self.workflow_rule_vendor_bill.tag_action_ids += tag_action_a

        invoice_test = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'name': 'invoice_test',
            'move_type': 'in_invoice',
        })
        self.env['documents.account.folder.setting'].create({
            'folder_id': self.folder_a.id,
            'journal_id': invoice_test.journal_id.id,
            'tag_ids': tag_b,
        })
        document_test = self.env['documents.document'].create({
            'name': 'test reconciliation workflow',
            'folder_id': self.folder_a.id,
            'datas': TEXT,
        })
        self.workflow_rule_vendor_bill.apply_actions([document_test.id])
        self.assertEqual(document_test.tag_ids, tag_a | tag_b,
            "The document should have the workflow action's tag(s)")

    def test_bridge_account_sync_partner(self):
        """
        Tests that the partner is always synced on the document, regardless of settings
        """
        partner_1, partner_2 = self.env['res.partner'].create([{'name': 'partner_1'}, {'name': 'partner_2'}])
        self.document_txt.partner_id = partner_1
        self.workflow_rule_vendor_bill.apply_actions([self.document_txt.id, self.document_gif.id])
        move = self.env['account.move'].browse(self.document_txt.res_id)
        self.assertEqual(move.partner_id, partner_1)
        move.partner_id = partner_2
        self.assertEqual(self.document_txt.partner_id, partner_2)
