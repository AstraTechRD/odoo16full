# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, new_test_user
import base64

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("TEST", 'utf-8'))
DATA = "data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
file_a = {'name': 'doc.zip', 'data': 'data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs='}
file_b = {'name': 'icon.zip', 'data': 'data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs='}


class TestCaseDocuments(TransactionCase):
    """ """
    def setUp(self):
        super(TestCaseDocuments, self).setUp()
        self.doc_user = self.env['res.users'].create({
            'name': 'Test user documents',
            'login': 'documents@example.com',
        })
        self.folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
        })
        self.folder_a_a = self.env['documents.folder'].create({
            'name': 'folder A - A',
            'parent_folder_id': self.folder_a.id,
        })
        self.folder_b = self.env['documents.folder'].create({
            'name': 'folder B',
        })
        self.tag_category_b = self.env['documents.facet'].create({
            'folder_id': self.folder_b.id,
            'name': "categ_b",
        })
        self.tag_b = self.env['documents.tag'].create({
            'facet_id': self.tag_category_b.id,
            'name': "tag_b",
        })
        self.tag_category_a = self.env['documents.facet'].create({
            'folder_id': self.folder_a.id,
            'name': "categ_a",
        })
        self.tag_category_a_a = self.env['documents.facet'].create({
            'folder_id': self.folder_a_a.id,
            'name': "categ_a_a",
        })
        self.tag_a_a = self.env['documents.tag'].create({
            'facet_id': self.tag_category_a_a.id,
            'name': "tag_a_a",
        })
        self.tag_a = self.env['documents.tag'].create({
            'facet_id': self.tag_category_a.id,
            'name': "tag_a",
        })
        self.document_gif = self.env['documents.document'].create({
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_b.id,
        })
        self.document_txt = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_b.id,
        })
        self.share_link_ids = self.env['documents.share'].create({
            'document_ids': [(4, self.document_txt.id, 0)],
            'type': 'ids',
            'name': 'share_link_ids',
            'folder_id': self.folder_a_a.id,
        })
        self.share_link_folder = self.env['documents.share'].create({
            'folder_id': self.folder_a_a.id,
            'name': "share_link_folder",
        })
        self.tag_action_a = self.env['documents.workflow.action'].create({
            'action': 'add',
            'facet_id': self.tag_category_b.id,
            'tag_id': self.tag_b.id,
        })
        self.worflow_rule = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a_a.id,
            'name': 'workflow rule on f_a_a',
            'folder_id': self.folder_b.id,
            'tag_action_ids': [(4, self.tag_action_a.id, 0)],
            'remove_activities': True,
            'activity_option': True,
            'activity_type_id': self.env.ref('documents.mail_documents_activity_data_Inbox').id,
            'activity_summary': 'test workflow rule activity summary',
            'activity_date_deadline_range': 7,
            'activity_date_deadline_range_type': 'days',
            'activity_note': 'activity test note',
        })

    def test_documents_create_from_attachment(self):
        """
        Tests a documents.document create method when created from an already existing ir.attachment.
        """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'attachmentGif.gif',
            'res_model': 'documents.document',
            'res_id': 0,
        })
        document_a = self.env['documents.document'].create({
            'folder_id': self.folder_b.id,
            'name': 'new name',
            'attachment_id': attachment.id,
        })
        self.assertEqual(document_a.attachment_id.id, attachment.id,
                         'the attachment should be the attachment given in the create values')
        self.assertEqual(document_a.name, 'new name',
                         'the name should be taken from the ir attachment')
        self.assertEqual(document_a.res_model, 'documents.document',
                         'the res_model should be set as document by default')
        self.assertEqual(document_a.res_id, document_a.id,
                         'the res_id should be set as its own id by default to allow access right inheritance')

    def test_documents_create_write(self):
        """
        Tests a documents.document create and write method,
        documents should automatically create a new ir.attachments in relevant cases.
        """
        document_a = self.env['documents.document'].create({
            'name': 'Test mimetype gif',
            'datas': GIF,
            'folder_id': self.folder_b.id,
        })
        self.assertEqual(document_a.res_model, 'documents.document',
                         'the res_model should be set as document by default')
        self.assertEqual(document_a.res_id, document_a.id,
                         'the res_id should be set as its own id by default to allow access right inheritance')
        self.assertEqual(document_a.attachment_id.datas, GIF, 'the document should have a GIF data')
        document_no_attachment = self.env['documents.document'].create({
            'name': 'Test mimetype gif',
            'folder_id': self.folder_b.id,
        })
        self.assertFalse(document_no_attachment.attachment_id, 'the new document shouldnt have any attachment_id')
        document_no_attachment.write({'datas': TEXT})
        self.assertEqual(document_no_attachment.attachment_id.datas, TEXT, 'the document should have an attachment')

    def test_documents_rules(self):
        """
        Tests a documents.workflow.rule
        """
        self.worflow_rule.apply_actions([self.document_gif.id, self.document_txt.id])
        self.assertTrue(self.tag_b.id in self.document_gif.tag_ids.ids, "failed at workflow rule add tag id")
        self.assertTrue(self.tag_b.id in self.document_txt.tag_ids.ids, "failed at workflow rule add tag id txt")
        self.assertEqual(len(self.document_gif.tag_ids.ids), 1, "failed at workflow rule add tag len")

        activity_gif = self.env['mail.activity'].search(['&',
                                                         ('res_id', '=', self.document_gif.id),
                                                         ('res_model', '=', 'documents.document')])

        self.assertEqual(len(activity_gif), 1, "failed at workflow rule activity len")
        self.assertTrue(activity_gif.exists(), "failed at workflow rule activity exists")
        self.assertEqual(activity_gif.summary, 'test workflow rule activity summary',
                         "failed at activity data summary from workflow create activity")
        self.assertEqual(activity_gif.note, '<p>activity test note</p>',
                         "failed at activity data note from workflow create activity")
        self.assertEqual(activity_gif.activity_type_id.id,
                         self.env.ref('documents.mail_documents_activity_data_Inbox').id,
                         "failed at activity data note from workflow create activity")

        self.assertEqual(self.document_gif.folder_id.id, self.folder_b.id, "failed at workflow rule set folder gif")
        self.assertEqual(self.document_txt.folder_id.id, self.folder_b.id, "failed at workflow rule set folder txt")

    def test_documents_rules_link_to_record(self):
        """
        Tests a documents.workflow.rule that links a document to a record.
        """
        workflow_rule_link = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule on link to record',
            'condition_type': 'criteria',
            'create_model': 'link.to.record',
        })
        user_admin_doc = new_test_user(self.env, login='Test admin documents', groups='documents.group_documents_manager,base.group_partner_manager')

        # prepare documents that the user owns
        Document = self.env['documents.document'].with_user(user_admin_doc)
        document_gif = Document.create({
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_b.id,
        })
        document_txt = Document.create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_b.id,
        })
        documents_to_link = [document_gif, document_txt]

        res_model = 'res.partner'
        record = {
            'res_model': res_model,
            'res_model_id': self.env['ir.model'].name_search(res_model, operator='=', limit=1)[0],
            'res_id': self.env[res_model].search([('type', '!=', 'private')], limit=1).id,
        }
        link_to_record_ctx = workflow_rule_link.apply_actions([doc.id for doc in documents_to_link])['context']
        link_to_record_wizard = self.env['documents.link_to_record_wizard'].with_user(user_admin_doc)\
                                                                           .with_context(link_to_record_ctx).create({})
        # Link record to document_gif and document_txt
        link_to_record_wizard.model_id = record['res_model_id']
        link_to_record_wizard.resource_ref = '%s,%s' % (record['res_model'], record['res_id'])
        link_to_record_wizard.link_to()

        for doc in documents_to_link:
            self.assertEqual(doc.res_model, record['res_model'], "bad model linked to the document")
            self.assertEqual(doc.res_id, record['res_id'], "bad record linked to the document")

        # Removes the link between document_gif and record
        workflow_rule_link.unlink_record([self.document_gif.id])
        self.assertNotEqual(self.document_gif.res_model, record['res_model'],
                            "the link between document_gif and its record was not correctly removed")
        self.assertNotEqual(self.document_gif.res_id, record['res_id'],
                            "the link between document_gif and its record was not correctly removed")

    def test_documents_rule_display(self):
        """
        tests criteria of rules
        """

        self.workflow_rule_criteria = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule on f_a & criteria',
            'condition_type': 'criteria',
            'required_tag_ids': [(6, 0, [self.tag_b.id])],
            'excluded_tag_ids': [(6, 0, [self.tag_a_a.id])]
        })

        self.assertFalse(self.workflow_rule_criteria.limited_to_single_record,
                         "this rule should not be limited to a single record")

        self.document_txt_criteria_a = self.env['documents.document'].create({
            'name': 'Test criteria a',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
            'tag_ids': [(6, 0, [self.tag_a_a.id, self.tag_b.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id not in self.document_txt_criteria_a.available_rule_ids.ids,
                        "failed at documents_workflow_rule unavailable rule")

        self.document_txt_criteria_b = self.env['documents.document'].create({
            'name': 'Test criteria b',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
            'tag_ids': [(6, 0, [self.tag_a.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id not in self.document_txt_criteria_b.available_rule_ids.ids,
                        "failed at documents_workflow_rule unavailable rule")
        self.document_txt_criteria_c = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
            'tag_ids': [(6, 0, [self.tag_b.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id in self.document_txt_criteria_c.available_rule_ids.ids,
                        "failed at documents_workflow_rule available rule")

        self.document_txt_criteria_d = self.env['documents.document'].create({
            'name': 'Test criteria d',
            'mimetype': 'text/plain',
            'folder_id': self.folder_b.id,
            'tag_ids': [(6, 0, [self.tag_b.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id not in self.document_txt_criteria_d.available_rule_ids.ids,
                        "failed at documents_workflow_rule unavailable rule")

    def test_documents_share_links(self):
        """
        Tests document share links
        """

        # by Folder
        vals = {
            'folder_id': self.folder_b.id,
            'domain': [],
            'tag_ids': [(6, 0, [])],
            'type': 'domain',
        }
        self.documents_share_links_a = self.env['documents.share'].create(vals)
        self.assertEqual(self.documents_share_links_a.type, 'domain', "failed at share link type domain")

        # by Folder with upload and activites
        vals = {
            'folder_id': self.folder_b.id,
            'domain': [],
            'tag_ids': [(6, 0, [])],
            'type': 'domain',
            'date_deadline': '3052-01-01',
            'action': 'downloadupload',
            'activity_option': True,
            'activity_type_id': self.ref('documents.mail_documents_activity_data_tv'),
            'activity_summary': 'test by Folder with upload and activites',
            'activity_date_deadline_range': 4,
            'activity_date_deadline_range_type': 'days',
            'activity_user_id': self.env.user.id,
        }
        self.share_folder_with_upload = self.env['documents.share'].create(vals)
        self.assertTrue(self.share_folder_with_upload.exists(), 'failed at upload folder creation')
        self.assertEqual(self.share_folder_with_upload.activity_type_id.name, 'To validate',
                         'failed at activity type for upload documents')
        self.assertEqual(self.share_folder_with_upload.state, 'live', "failed at share_link live")

        # by documents
        vals = {
            'document_ids': [(6, 0, [self.document_gif.id, self.document_txt.id])],
            'folder_id': self.folder_b.id,
            'date_deadline': '2001-11-05',
            'type': 'ids',
        }
        self.result_share_documents_act = self.env['documents.share'].create(vals)

        # Expiration date
        self.assertEqual(self.result_share_documents_act.state, 'expired', "failed at share_link expired")

    def test_documents_share_popup(self):
        share_folder = self.env['documents.folder'].create({
            'name': 'share folder',
        })
        share_tag_category = self.env['documents.facet'].create({
            'folder_id': share_folder.id,
            'name': "share category",
        })
        share_tag = self.env['documents.tag'].create({
            'facet_id': share_tag_category.id,
            'name': "share tag",
        })
        domain = [('folder_id', 'in', share_folder.id)]
        action = self.env['documents.share'].open_share_popup({
            'domain': domain,
            'folder_id': share_folder.id,
            'tag_ids': [[6, 0, [share_tag.id]]],
            'type': 'domain',
        })
        action_context = action['context']
        self.assertTrue(action_context)
        self.assertEqual(action_context['default_owner_id'], self.env.uid, "the action should open a view with the current user as default owner")
        self.assertEqual(action_context['default_folder_id'], share_folder.id, "the action should open a view with the right default folder")
        self.assertEqual(action_context['default_tag_ids'], [[6, 0, [share_tag.id]]], "the action should open a view with the right default tags")
        self.assertEqual(action_context['default_type'], 'domain', "the action should open a view with the right default type")
        self.assertEqual(action_context['default_domain'], domain, "the action should open a view with the right default domain")

    def test_request_activity(self):
        """
        Makes sure the document request activities are working properly
        """
        partner = self.env['res.partner'].create({'name': 'Pepper Street'})
        activity_type = self.env['mail.activity.type'].create({
            'name': 'test_activity_type',
            'category': 'upload_file',
            'folder_id': self.folder_a.id,
        })
        activity = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'user_id': self.doc_user.id,
            'res_id': partner.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1).id,
            'summary': 'test_summary',
        })

        activity_2 = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'user_id': self.doc_user.id,
            'res_id': partner.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1).id,
            'summary': 'test_summary_2',
        })

        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'Test activity 1',
        })

        attachment_2 = self.env['ir.attachment'].create({
            'datas': TEXT,
            'name': 'Test activity 2',
        })
        document_1 = self.env['documents.document'].search([('request_activity_id', '=', activity.id)], limit=1)
        document_2 = self.env['documents.document'].search([('request_activity_id', '=', activity_2.id)], limit=1)

        self.assertEqual(document_1.name, 'test_summary', 'the activity document should have the right name')
        self.assertEqual(document_1.folder_id.id, self.folder_a.id, 'the document 1 should have the right folder')
        self.assertEqual(document_2.folder_id.id, self.folder_a.id, 'the document 2 should have the right folder')
        activity._action_done(attachment_ids=[attachment.id])
        document_2.write({'datas': TEXT, 'name': 'new filename'})
        self.assertEqual(document_1.attachment_id.id, attachment.id,
                         'the document should have the newly added attachment')
        self.assertFalse(activity.exists(), 'the activity should be done')
        self.assertFalse(activity_2.exists(), 'the activity_2 should be done')

    def test_recurring_document_request(self):
        """
        Ensure that separate document requests are created for recurring upload activities
        Ensure that the next activity is linked to the new document
        """
        activity_type = self.env['mail.activity.type'].create({
            'name': 'recurring_upload_activity_type',
            'category': 'upload_file',
            'folder_id': self.folder_a.id,
        })
        activity_type.write({
            'chaining_type': 'trigger',
            'triggered_next_type_id': activity_type.id
        })
        document = self.env['documents.request_wizard'].create({
            'name': 'Wizard Request',
            'owner_id': self.doc_user.id,
            'activity_type_id': activity_type.id,
            'folder_id': self.folder_a.id,
        }).request_document()
        activity = document.request_activity_id

        self.assertEqual(activity.summary, 'Wizard Request')

        document.write({'datas': GIF, 'name': 'testGif.gif'})

        self.assertFalse(activity.exists(), 'the activity should be removed after file upload')
        self.assertEqual(document.type, 'binary', 'document 1 type should be binary')
        self.assertFalse(document.request_activity_id, 'document 1 should have no activity remaining')

        # a new document (request) and file_upload activity should be created
        activity_2 = self.env['mail.activity'].search([('res_model', '=', 'documents.document')])
        document_2 = self.env['documents.document'].search([('request_activity_id', '=', activity_2.id), ('type', '=', 'empty')])

        self.assertNotEqual(document_2.id, document.id, 'a new document and activity should exist')
        self.assertEqual(document_2.request_activity_id.summary, 'Wizard Request')

    def test_default_res_id_model(self):
        """
        Test default res_id and res_model from context are used for linking attachment to document.
        """
        document = self.env['documents.document'].create({'folder_id': self.folder_b.id})
        attachment = self.env['ir.attachment'].with_context(
            default_res_id=document.id,
            default_res_model=document._name,
        ).create({
            'name': 'attachmentGif.gif',
            'datas': GIF,
        })
        self.assertEqual(attachment.res_id, document.id, "It should be linked to the default res_id")
        self.assertEqual(attachment.res_model, document._name, "It should be linked to the default res_model")
        self.assertEqual(document.attachment_id, attachment, "Document should be linked to the created attachment")

    def test_versioning(self):
        """
        Tests the versioning/history of documents
        """
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
        self.assertEqual(len(document.previous_attachment_ids.ids), 0, "The history should be empty")
        document.write({'datas': TEXT})
        self.assertEqual(len(document.previous_attachment_ids.ids), 1, "There should be 1 attachment in history")
        self.assertEqual(document.previous_attachment_ids[0].datas, GIF, "The history should have the right content")
        old_attachment = document.previous_attachment_ids[0]
        new_attachment = document.attachment_id
        document.write({'attachment_id': old_attachment.id})
        self.assertEqual(len(document.previous_attachment_ids.ids), 1, "there should still be 1 attachment in history")
        self.assertEqual(document.attachment_id.id, old_attachment.id, "the history should contain the old attachment")
        self.assertEqual(document.previous_attachment_ids[0].id, new_attachment.id,
                         "the document should contain the new attachment")

    def test_write_mimetype(self):
        """
        Tests the consistency of documents' mimetypes
        """
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/plain'})
        self.assertEqual(document.mimetype, 'text/plain', "the new mimetype should be the one given on write")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'})
        self.assertEqual(document.mimetype, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', "should preserve office mime type")

    def test_cascade_delete(self):
        """
        Makes sure that documents are unlinked when their attachment is unlinked.
        """
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
        self.assertTrue(document.exists(), 'the document should exist')
        document.attachment_id.unlink()
        self.assertFalse(document.exists(), 'the document should not exist')

    def test_is_favorited(self):
        user = new_test_user(self.env, "test user", groups='documents.group_documents_user')
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
        document.favorited_ids = user
        self.assertFalse(document.is_favorited)
        self.assertTrue(document.with_user(user).is_favorited)

    def test_neuter_mimetype(self):
        """
        Tests that potentially harmful mimetypes (XML mimetypes that can lead to XSS attacks) are converted to text

        In fact this logic is implemented in the base `IrAttachment` model but was originally duplicated.  
        The test stays duplicated here to ensure the de-duplicated logic still catches our use cases.
        """
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})

        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XML mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'image/svg+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "SVG mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/html'})
        self.assertEqual(document.mimetype, 'text/plain', "HTML mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'application/xhtml+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XHTML mimetype should be forced to text")

    def test_create_from_message(self):
        """
        When we create the document from a message, we need to apply the defaults set on the share.
        """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'attachmentGif.gif',
            'res_model': 'documents.document',
            'res_id': 0,
        })
        partner = self.env['res.partner'].create({
            'name': 'Luke Skywalker'
        })
        share = self.env['documents.share'].create({
            'owner_id': self.doc_user.id,
            'partner_id': partner.id,
            'tag_ids': [(6, 0, [self.tag_b.id])],
            'folder_id': self.folder_a.id,
        })
        message = self.env['documents.document'].message_new({
            'subject': 'test message'
        }, {
            # this create_share_id value, is normally passed from the alias default created by the share
            'create_share_id': share.id,
            'folder_id': self.folder_a.id,
        })
        message._message_post_after_hook({ }, {
            'attachment_ids': [(4, attachment.id)]
        })
        self.assertEqual(message.active, False, 'Document created for the message should be inactive')
        self.assertNotEqual(attachment.res_id, 0, 'Should link document to attachment')
        attachment_document = self.env['documents.document'].browse(attachment.res_id)
        self.assertNotEqual(attachment_document, None, 'Should have created document')
        self.assertEqual(attachment_document.owner_id.id, self.doc_user.id, 'Should assign owner from share')
        self.assertEqual(attachment_document.partner_id.id, partner.id, 'Should assign partner from share')
        self.assertEqual(attachment_document.tag_ids.ids, [self.tag_b.id], 'Should assign tags from share')

    def test_create_from_message_invalid_tags(self):
        """
        Create a new document from message with a deleted tag, it should keep only existing tags.
        """
        message = self.env['documents.document'].message_new({
            'subject': 'Test',
        }, {
            'tag_ids': [(6, 0, [self.tag_b.id, -1])],
            'folder_id': self.folder_a.id,
        })
        self.assertEqual(message.tag_ids.ids, [self.tag_b.id], "Should only keep the existing tag")
