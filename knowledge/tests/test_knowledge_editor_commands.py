# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.tests.common import tagged, HttpCase


@tagged('post_install', '-at_install', 'knowledge', 'knowledge_tour')
class TestKnowledgeEditorCommands(HttpCase):
    """
    This test suit run tours to test the new editor commands of Knowledge.
    """
    @classmethod
    def setUpClass(cls):
        super(TestKnowledgeEditorCommands, cls).setUpClass()
        # remove existing articles to ease tour management
        cls.env['knowledge.article'].search([]).unlink()
        cls.env['knowledge.article'].create({
            'body': Markup('<p><br></p>')
        })

    def knowledge_article_command_tour(self):
        """Test the /article command in the editor"""
        self.start_tour('/web', 'knowledge_article_command_tour', login='admin', step_delay=100)

    def knowledge_file_command_tour(self):
        """Test the /file command in the editor"""
        self.start_tour('/web', 'knowledge_file_command_tour', login='admin', step_delay=100)

    def knowledge_index_command_tour(self):
        """Test the /index command in the editor"""
        self.start_tour('/web', 'knowledge_index_command_tour', login='admin', step_delay=100)

    def knowledge_kanban_command_tour(self):
        """Test the /kanban command in the editor"""
        self.start_tour('/web', 'knowledge_kanban_command_tour', login='admin', step_delay=100)

    def knowledge_list_command_tour(self):
        """Test the /list command in the editor"""
        self.start_tour('/web', 'knowledge_list_command_tour', login='admin', step_delay=100)

    def knowledge_outline_command_tour(self):
        """Test the /outline command in the editor"""
        self.start_tour('/web', 'knowledge_outline_command_tour', login='admin', step_delay=100)

    def knowledge_table_of_content_command_tour(self):
        """Test the /toc command in the editor"""
        self.start_tour('/web', 'knowledge_table_of_content_command_tour', login='admin', step_delay=100)

    def knowledge_template_command_tour(self):
        """Test the /template command in the editor"""
        self.start_tour('/web', 'knowledge_template_command_tour', login='admin', step_delay=100)
