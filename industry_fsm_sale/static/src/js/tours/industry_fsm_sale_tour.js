/** @odoo-module */
/**
 * Add custom steps to take products and sales order into account
 */
import tour from 'web_tour.tour';
import 'industry_fsm.tour';
import { _t } from 'web.core';
import { Markup } from 'web.utils';

const fsmStartStepIndex = tour.tours.industry_fsm_tour.steps.findIndex(step => step.id === 'fsm_start');

tour.tours.industry_fsm_tour.steps.splice(fsmStartStepIndex + 1, 0, {
    trigger: 'button[name="action_fsm_view_material"]',
    extra_trigger: 'button[name="action_timer_stop"]',
    content: _t('Let\'s <b>track the material</b> you use for your task.'),
    position: 'bottom',
}, {
    trigger: ".o-kanban-button-new",
    content: _t('Let\'s create a new <b>product</b>.'),
    position: 'right',
}, {
    trigger: '.o_field_char input',
    content: Markup(_t('Choose a <b>name</b> for your product <i>(e.g. Bolts, Screws, Boiler, etc.).</i>')),
    position: 'right',
}, {
    trigger: ".o_form_button_save",
    content: _t("Save your <b>product</b>."),
    position: "bottom",
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: ".o_form_saved",
    content: Markup(_t("Use the breadcrumbs to navigate to your <b>list of products</b>.")),
    position: "bottom",
}, {
    trigger: "button[name='fsm_add_quantity']",
    alt_trigger: ".o_fsm_material_kanban .o_kanban_record",
    extra_trigger: '.o_fsm_material_kanban',
    content: _t('Click on your product to add it to your <b>list of materials</b>. <i>Tip: for large quantities, click on the number to edit it directly.</i>'),
    position: 'right',
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_fsm_material_kanban',
    content: Markup(_t("Use the breadcrumbs to return to your <b>task</b>.")),
    position: "bottom"
});

const fsmCreateInvoiceStepIndex = tour.tours.industry_fsm_tour.steps.findIndex(step => step.id === 'fsm_invoice_create');

tour.tours.industry_fsm_tour.steps.splice(fsmCreateInvoiceStepIndex + 1, 0, {
    trigger: ".o_statusbar_buttons > button:contains('Create Invoice')",
    content: _t("<b>Invoice your time and material</b> to your customer."),
    position: "bottom"
}, {
    trigger: ".modal-footer button[id='create_invoice_open'].btn-primary",
    extra_trigger: ".modal-dialog.modal-lg",
    content: _t("Confirm the creation of your <b>invoice</b>."),
    position: "bottom"
}, {
    content: _t("Wait for the invoice to show up"),
    trigger: "span:contains('Customer Invoice')",
    run() {},
    auto: true,
});
