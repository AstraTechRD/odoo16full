odoo.define('documents_account.tour', function(require) {
"use strict";

const { _t } = require('web.core');
const {Markup} = require('web.utils');
const tour = require('web_tour.tour');

const { markup } = owl;

tour.register('documents_account_tour', {
    url: "/web",
    rainbowManMessage: markup(_t("Wow... 6 documents processed in a few seconds, You're good.<br/>The tour is complete. Try uploading your own documents now.")),
    sequence: 170,
}, [{
    trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
    content: Markup(_t("Want to become a <b>paperless company</b>? Let's discover Odoo Documents.")),
    position: 'bottom',
}, {
    trigger: 'img[src="https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg"]',
    content: Markup(_t("Click on a thumbnail to <b>preview the document</b>.")),
    position: 'bottom',
    run: function (actions) {
        // closes the modal
        $('.o_close_btn').click();
    },
}, { // equivalent to '.o_search_panel_filter_value:contains('Inbox')' but language agnostic.
    trigger: '.o_search_panel_filter_value:eq(0)',
    extra_trigger: '.o_search_panel_label',
    content: Markup(_t("Let's process documents in your Inbox.<br/><i>Tip: Use Tags to filter documents and structure your process.</i>")),
    position: 'bottom',
    run: function (actions) {
        $('.o_search_panel_filter_value:eq(0) .o_search_panel_label_title').click();
    },
}, {
    trigger: '.o_kanban_record:contains(mail.png)',
    extra_trigger: '.o_documents_kanban',
    content: Markup(_t("Click on a card to <b>select the document</b>.")),
    position: 'bottom',
}, { // equivalent to '.o_inspector_rule:contains('Send to Legal') .o_inspector_trigger_rule' but language agnostic.
    trigger: '.o_inspector_rule[data-id="3"] .o_inspector_trigger_rule',
    extra_trigger: '.o_documents_image_background',
    content: Markup(_t("Let's tag this mail as legal<br/> <i>Tips: actions can be tailored to your process, according to the workspace.</i>")),
    position: 'bottom',
}, { // the nth(0) ensures that the filter of the preceding step has been applied.
    trigger: '.o_kanban_record:nth(0):contains(Mails_inbox.pdf)',
    extra_trigger: '.o_documents_kanban',
    content: _t("Let's process this document, coming from our scanner."),
    position: 'bottom',
}, {
    trigger: '.o_inspector_split',
    extra_trigger: '[title="Mails_inbox.pdf"]',
    content: _t("As this PDF contains multiple documents, let's split and process in bulk."),
    position: 'bottom',
}, {
    trigger: '.o_page_splitter_wrapper:nth(3)',
    extra_trigger: '.o_documents_pdf_canvas:nth(5)', // Makes sure that all the canvas are loaded.
    content: Markup(_t("Click on the <b>page separator</b>: we don't want to split these two pages as they belong to the same document.")),
    position: 'right',
}, {
    trigger: '.o_documents_pdf_page_selector:nth(5)',
    extra_trigger: '.o_documents_pdf_manager',
    content: Markup(_t("<b>Deselect this page</b> as we plan to process all bills first.")),
    position: 'left',
}, { // equivalent to '.o_pdf_rule_buttons:contains(Scan Bill)' but language agnostic.
    trigger: '.o_pdf_rule_buttons:nth-last-child(2)',
    extra_trigger: '.o_documents_pdf_manager',
    content: _t("Let's process these bills: turn them into vendor bills."),
    position: 'bottom',
}, { // equivalent to '.o_pdf_rule_buttons:contains(Send to Legal)' but language agnostic.
    trigger: '.o_pdf_rule_buttons:first',
    extra_trigger: '.o_pdf_rule_buttons:not(:disabled)',
    content: _t("Send this letter to the legal department, by assigning the right tags."),
    position: 'bottom',
}]);
});
