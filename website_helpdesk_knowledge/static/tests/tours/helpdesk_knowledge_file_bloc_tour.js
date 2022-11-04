/** @odoo-module */

import tour from 'web_tour.tour';


tour.register('helpdesk_pick_file_as_attachment_from_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_action_main_tree',
    test: true,
}, [{ // click on the first record of the list
    trigger: 'tr.o_data_row:first-child .o_data_cell[name="name"]',
    run: 'click',
}, { // open an article
    trigger: 'button[title="Search Knowledge Articles"]',
    run: 'click',
}, { // click on the first command of the command palette
    trigger: '.o_command_palette_listbox #o_command_0',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // click on the "Use as Attachment" button located in the toolbar of the file block
    trigger: '.o_knowledge_behavior_type_file .o_knowledge_toolbar_button_text:contains("Use as Attachment")',
    run: 'click',
}, { // check that the file is added to the attachments
    trigger: '.o_AttachmentBox .o_AttachmentImage',
}]);

tour.register('helpdesk_pick_file_as_message_attachment_from_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_action_main_tree',
    test: true,
}, [{ // click on the first record of the list
    trigger: 'tr.o_data_row:first-child .o_data_cell[name="name"]',
    run: 'click',
}, { // open an article
    trigger: 'button[title="Search Knowledge Articles"]',
    run: 'click',
}, { // click on the first command of the command palette
    trigger: '.o_command_palette_listbox #o_command_0',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // click on the "Use as Attachment" button located in the toolbar of the file block
    trigger: '.o_knowledge_behavior_type_file .o_knowledge_toolbar_button_text:contains("Send as Message")',
    run: 'click',
}, { // check that the file is added to the attachment of the message
    trigger: '.o_Chatter_composer .o_AttachmentImage',
}]);
