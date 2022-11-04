/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('rental_product_configurator_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale_renting.rental_menu_root"]',
    edition: 'enterprise'
}, {
    trigger: '.o-kanban-button-new',
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")'
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custom',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
},
// Product Configurator Wizard
{
    trigger: '.main_product span:contains("Steel")',
}, {
    trigger: '.main_product span:contains("Aluminium")',
}, {
    trigger: 'input[data-value_name="Black"]'
}, {
    trigger: '.btn-primary.disabled',
    extra_trigger: '.show .modal-footer'
}, {
    trigger: 'input[data-value_name="White"]'
}, {
    trigger: '.btn-primary:not(.disabled)',
    extra_trigger: '.show .modal-footer'
}, {
    trigger: '.js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
    id: 'quotation_product_selected',
},
// Rental Wizard
{
    trigger: 'button[special=save]',
    extra_trigger: '.o_form_nosheet',
    position: 'bottom',
},

// Editing a custom desk => reopen the rental wizard
{
    trigger: '[name="product_template_id"] span:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'button.fa-calendar',
    extra_trigger: '[data-tooltip*=Customizable]',
},{
    trigger: 'div[name="qty_to_reserve"] input',
    run: 'text 2',
}, {
    trigger: 'div[name="unit_price"] input',
    run: 'text 42',
}, {
    trigger: 'button[special=save]',
    extra_trigger: '.o_form_nosheet',
    position: 'bottom',
},

// Adding a line with a more expensive custom desk
{
    trigger: 'a:contains("Add a product")',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custom',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
},
// Product Configurator Wizard
{
    trigger: '.main_product span:contains("Steel")',
}, {
    trigger: 'input[data-value_name="White"]'
}, {
    trigger: '.btn-primary:not(.disabled)',
    extra_trigger: '.show .modal-footer'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
    id: 'quotation_product_selected',
},
// Rental Wizard
{
    trigger: 'div[name="qty_to_reserve"] input',
    run: 'text 5',
}, {
    trigger: 'button[special=save]',
    extra_trigger: '.o_form_nosheet',
    position: 'bottom',
}, {
    trigger: 'button[name=action_confirm]',
    position: 'bottom',
}, {
    content: "verify that the rental has been confirmed",
    trigger: '.o_statusbar_status button.o_arrow_button_current:contains("Sales Order")',
    run() {},
}, ...tour.stepUtils.discardForm(),
]);
