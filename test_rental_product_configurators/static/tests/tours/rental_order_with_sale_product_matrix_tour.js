/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('rental_order_with_sale_product_matrix_tour', {
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
},
// Adding a sale product without any configurator
{
    trigger: 'a:contains("Add a product")'
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text protection',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Chair floor protection (TEST)")',
},
// Adding a rental product
{
    trigger: 'a:contains("Add a product")',
    extra_trigger: '[name="name"][data-tooltip*="floor protection"]',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Projector',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Projector (TEST)")',
}, {
    trigger: 'button[special=save]',
    extra_trigger: '.o_form_nosheet',
    position: 'bottom',
},
// Adding a sale product with a matrix
{
    trigger: 'a:contains("Add a product")',
    extra_trigger: '[name="name"][data-tooltip*="Projector"]',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Matrix',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Matrix")',
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        $('.o_matrix_input').slice(8, 16).val(4);
    } // set the qty to 4 for half of the matrix products.
}, {
    trigger: 'span:contains("Confirm")',
},
    ...tour.stepUtils.saveForm({ extra_trigger: '.o_field_cell.o_data_cell.o_list_number:contains("26")' }),
]);
