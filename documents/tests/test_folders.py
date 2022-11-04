# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import Command
from odoo.tests.common import TransactionCase


class TestDocumentsFolder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_folder = cls.env['documents.folder'].create({'name': 'Parent'})
        cls.folder = cls.env['documents.folder'].create({'name': 'Folder', 'parent_folder_id': cls.parent_folder.id})
        cls.child_folder = cls.env['documents.folder'].create({'name': 'Child', 'parent_folder_id': cls.folder.id})
        cls.folders = cls.env['documents.folder'] | cls.parent_folder | cls.folder | cls.child_folder

    def test_is_shared(self):
        self.assertFalse(any(folder.is_shared for folder in (self.parent_folder, self.folder, self.child_folder)), "None of the folders should be shared by default")

        share_link = self.env['documents.share'].create({
            'folder_id': self.folder.id,
            'include_sub_folders': False,
            'type': 'domain',
        })
        self.folders._compute_is_shared()

        self.assertTrue(self.folder.is_shared, "The folder should be shared")
        self.assertFalse(any((self.parent_folder.is_shared, self.child_folder.is_shared)), "The parent and child folders should not be shared")

        share_link.write({'include_sub_folders': True})
        self.folders._compute_is_shared()

        self.assertTrue(all((self.folder.is_shared, self.child_folder.is_shared)), "The folder and its children should be shared")
        self.assertFalse(self.parent_folder.is_shared, "The parent folder should not be shared")

        share_link.write({'date_deadline': date.today() + timedelta(days=-1)})
        self.folders._compute_is_shared()

        self.assertFalse(any(folder.is_shared for folder in (self.parent_folder, self.folder, self.child_folder)), "None of the folders should be shared by an expired link")

        share_link.write({'date_deadline': date.today() + timedelta(days=1)})
        self.folders._compute_is_shared()

        self.assertTrue(self.folder.is_shared and self.child_folder.is_shared, "The folder and its children should be shared by a link not yet expired")

    def test_folder_copy(self):
        original_folder = self.env['documents.folder'].create({
            'name': 'Template',
        })
        child_folder = self.env['documents.folder'].create({
            'name': 'Child Folder',
            'parent_folder_id': original_folder.id,
        })
        facet = self.env['documents.facet'].create({
            'name': 'Facet',
            'folder_id': child_folder.id,
        })
        tag_1 = self.env['documents.tag'].create({
            'name': 'Tag 1',
            'facet_id': facet.id,
        })
        tag_2 = self.env['documents.tag'].create({
            'name': 'Tag 2',
            'facet_id': facet.id,
        })
        workflow_rule = self.env['documents.workflow.rule'].create({
            'name': 'Rule',
            'domain_folder_id': child_folder.id,
            'condition_type': 'criteria',
            'required_tag_ids': [Command.link(tag_1.id)],
            'excluded_tag_ids': [Command.link(tag_2.id)],
        })
        self.env['documents.workflow.action'].create({
            'workflow_rule_id': workflow_rule.id,
            'action': 'add',
            'facet_id': facet.id,
            'tag_id': tag_2.id,
        })

        copied_folder = original_folder.copy()
        self.assertEqual(original_folder.name, copied_folder.name, "The copied folder should have the same name as the original")

        self.assertEqual(len(copied_folder.children_folder_ids), 1, "The sub workspaces of the template should also be copied.")
        child_folder_copy = copied_folder.children_folder_ids[0]

        self.assertEqual(len(child_folder_copy.facet_ids), 1, "The copied workspaces should retain their facets.")
        facet_copy = child_folder_copy.facet_ids[0]
        self.assertEqual(facet.name, facet_copy.name, "The copied workspaces should retain their facets.")

        self.assertEqual(len(facet_copy.tag_ids), 2, "The copied facets should retain the same tags.")
        self.assertCountEqual([tag.name for tag in facet.tag_ids], [tag.name for tag in facet_copy.tag_ids], "The copied facets should retain the same tags.")
        tag_1_copy, tag_2_copy = facet_copy.tag_ids

        workflow_rule_copy_search = self.env['documents.workflow.rule'].search([('domain_folder_id', '=', child_folder_copy.id)])
        self.assertEqual(len(workflow_rule_copy_search), 1, "The copied workspaces should retain their workflow rules.")
        workflow_rule_copy = workflow_rule_copy_search[0]
        self.assertEqual(workflow_rule.name, workflow_rule_copy.name, "The copied workspaces should retain their workflow rules.")
        self.assertCountEqual(workflow_rule_copy.required_tag_ids.ids, [tag_1_copy.id], "The copied workflow rules should retain their required tags.")
        self.assertCountEqual(workflow_rule_copy.excluded_tag_ids.ids, [tag_2_copy.id], "The copied workflow rules should retain their excluded tags.")

        workflow_actions = self.env['documents.workflow.action'].search([('workflow_rule_id', '=', workflow_rule_copy.id), ('facet_id', '=', facet_copy.id), ('tag_id', '=', tag_2_copy.id)])
        self.assertEqual(len(workflow_actions), 1, "The actions linked to the workspace should be copied and retain their properties")

    def test_folder_copy_rule_move_folder(self):
        """
        Tests copying a folder with an associated action that moves the document
        to a different unrelated folder and adds a tag from that other folder.
        The references to the other folder and its tag should be kept identical.
        """
        original_folder, other_folder = self.env['documents.folder'].create([
            {'name': 'Original Folder'}, {'name': 'Other Folder'},
        ])
        other_folder_facet = self.env['documents.facet'].create({
            'name': 'Other Folder Facet',
            'folder_id': other_folder.id,
        })
        other_folder_tag = self.env['documents.tag'].create({
            'name': 'Other Folder Tag',
            'facet_id': other_folder_facet.id,
        })
        workflow_rule = self.env['documents.workflow.rule'].create({
            'name': 'Rule',
            'domain_folder_id': original_folder.id,
            'condition_type': 'criteria',
            'folder_id': other_folder.id,
        })
        workflow_action = self.env['documents.workflow.action'].create({
            'workflow_rule_id': workflow_rule.id,
            'facet_id': other_folder_facet.id,
            'tag_id': other_folder_tag.id,
        })

        copied_folder = original_folder.copy()
        workflow_rule_copy = self.env['documents.workflow.rule'].search([('domain_folder_id', '=', copied_folder.id)])[0]
        self.assertEqual(workflow_rule.folder_id.id, workflow_rule_copy.folder_id.id, "The value of the folder the documents are moved to should be kept identical.")

        workflow_action_copy = self.env['documents.workflow.action'].search([('workflow_rule_id', '=', workflow_rule_copy.id)])[0]
        self.assertEqual(workflow_action_copy.facet_id.id, workflow_action.facet_id.id, "The value of the facet should be kept identical.")
        self.assertEqual(workflow_action_copy.tag_id.id, workflow_action.tag_id.id, "The value of the tag should be kept identical.")

    def test_folder_copy_ancestor_tag(self):
        """
        Tests copying subfolders with associated workflow actions using tags from ancestor folders.
        If the ancestor is being copied in the same copy, the tags should be changed accordingly.
        Else, the tags should not be set on the copied folder.
        """
        folder = self.env['documents.folder'].create({'name': 'Folder'})
        sub_folder = self.env['documents.folder'].create({
            'name': 'Sub Folder',
            'parent_folder_id': folder.id,
        })
        sub_sub_folder = self.env['documents.folder'].create({
            'name': 'Sub sub folder',
            'parent_folder_id': sub_folder.id,
        })
        folder_facet, sub_folder_facet = self.env['documents.facet'].create([
            {'name': 'Folder facet', 'folder_id': folder.id},
            {'name': 'Sub folder facet', 'folder_id': sub_folder.id},
        ])
        folder_tag, sub_folder_tag = self.env['documents.tag'].create([
            {'name': 'Folder tag', 'facet_id': folder_facet.id},
            {'name': 'Sub folder tag', 'facet_id': sub_folder_facet.id},
        ])
        rule = self.env['documents.workflow.rule'].create({
            'name': 'Rule',
            'domain_folder_id': sub_sub_folder.id,
            'required_tag_ids': [Command.link(folder_tag.id)],
            'excluded_tag_ids': [Command.link(sub_folder_tag.id)],
        })
        self.env['documents.workflow.action'].create([
            {
                'workflow_rule_id': rule.id,
                'action': 'remove',
                'facet_id': folder_facet.id,
                'tag_id': folder_tag.id,
            },
            {
                'workflow_rule_id': rule.id,
                'action': 'add',
                'facet_id': sub_folder_facet.id,
                'tag_id': sub_folder_tag.id,
            },
        ])

        sub_folder_copy = sub_folder.copy()
        sub_folder_facet_copy = sub_folder_copy.facet_ids[0]
        sub_folder_tag_copy = sub_folder_facet_copy.tag_ids[0]
        sub_sub_folder_copy = sub_folder_copy.children_folder_ids[0]
        rule_copy = self.env['documents.workflow.rule'].search([('domain_folder_id', '=', sub_sub_folder_copy.id)])
        action_1_copy = self.env['documents.workflow.action'].search([('workflow_rule_id', '=', rule_copy.id), ('action', '=', 'remove')])
        action_2_copy = self.env['documents.workflow.action'].search([('workflow_rule_id', '=', rule_copy.id), ('action', '=', 'add')])

        self.assertEqual(rule_copy.required_tag_ids.ids, [], "The required tags of the copied rule should be empty.")
        self.assertCountEqual(rule_copy.excluded_tag_ids.ids, sub_folder_tag_copy.ids, "The excluded tags of the copied rule should be updated to use the copied tags of the parent folder.")
        self.assertFalse(action_1_copy.facet_id and action_1_copy.tag_id, "The copy of the first action should have no facet and tag set")
        self.assertEqual((action_2_copy.facet_id.id, action_2_copy.tag_id.id), (sub_folder_facet_copy.id, sub_folder_tag_copy.id), "The facet and tag of the copy of the second action should be updated to use the copied tag and facet of the parent folder.")
