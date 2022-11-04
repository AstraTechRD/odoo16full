# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.tests.common import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestHelpdeskKnowledgeCrossModuleFeatures(HttpCase):
    """
    This test suit will test the "cross-module" features of Knowledge.
    """
    @classmethod
    def setUpClass(cls):
        super(TestHelpdeskKnowledgeCrossModuleFeatures, cls).setUpClass()
        cls.env['knowledge.article'].search([]).unlink()
        cls.env['knowledge.article'].create({
            'body': Markup("""
                <p><br></p>
                <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_template">
                    <div class="d-flex">
                        <div class="o_knowledge_template_label align-middle">Template</div>
                    </div>
                    <div class="o_knowledge_content" data-prop-name="content">
                        <p>Hello world</p>
                    </div>
                </div>
                <p><br></p>
                <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_file">
                    <div class="o_knowledge_file_image" data-prop-name="fileImage">
                        <a href="https://www.odoo.com/web/content/31413934?download=true" title="Onboarding.pdf" data-mimetype="application/pdf" class="o_image"></a>
                    </div>
                    <div class="o_knowledge_file_description">
                        <div class="o_knowledge_file_name" data-prop-name="fileName">Odoo Survival Guide</div>
                        <div class="o_knowledge_file_extension" data-prop-name="fileExtension">pdf</div>
                    </div>
                </div>
                <p><br></p>
            """)
        })

    # Embedded view block:

    def helpdesk_insert_graph_view_in_knowledge(self):
        """This tour will check that the user can insert a graph view in an article."""
        self.start_tour('/web#action=helpdesk.helpdesk_ticket_analysis_action',
            'helpdesk_insert_graph_view_in_knowledge', login='admin', step_delay=100)

    def helpdesk_insert_kanban_view_link_in_knowledge(self):
        """This tour will check that the user can insert a view link in an article."""
        self.start_tour('/web#action=helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_insert_kanban_view_link_in_knowledge', login='admin', step_delay=100)

    # File block:

    def helpdesk_pick_file_as_attachment_from_knowledge(self):
        self.start_tour('/web#action=helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_file_as_attachment_from_knowledge', login='admin', step_delay=100)

    def helpdesk_pick_file_as_message_attachment_from_knowledge(self):
        self.start_tour('/web#action=helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_file_as_message_attachment_from_knowledge', login='admin', step_delay=100)

    # Template block:

    def helpdesk_pick_template_as_description_from_knowledge(self):
        self.start_tour('/web#action=helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_template_as_description_from_knowledge', login='admin', step_delay=100)

    def helpdesk_pick_template_as_message_from_knowledge(self):
        self.start_tour('/web#action=helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_template_as_message_from_knowledge', login='admin', step_delay=100)
