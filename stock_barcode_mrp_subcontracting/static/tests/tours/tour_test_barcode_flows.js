odoo.define('test_barcode_subcontract_flows.tour', function (require) {
'use strict';

var core = require('web.core');
var tour = require('web_tour.tour');
var helper = require('stock_barcode.tourHelper');


var _t = core._t;

// ----------------------------------------------------------------------------
// Tours
// ----------------------------------------------------------------------------

tour.register('test_receipt_classic_subcontracted_product', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            const button = document.querySelector('button.o_mrp_subcontracting');
            helper.assert(button, null, "Button record component shouldn't be in the DOM");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product_subcontracted',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    // Adds a line with the "Add Product" button, then scans its destination location.
    { trigger: '.o_add_line' },
    {
        trigger: '.o_field_widget[name=product_id] input',
        run: 'text Chocolate Eclairs',
    },
    { trigger: ".ui-menu-item > a:contains('Chocolate Eclairs')" },
    {
        trigger: '[name=qty_done] input',
        run: 'text 1',
    },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOC-01-02-00',
    },
    ...tour.stepUtils.validateBarcodeForm(),

]);

tour.register('test_receipt_tracked_subcontracted_product', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product_subcontracted',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        position: "right",
        run: "text 1",
    },

    {
        trigger: ".modal-footer .btn[name=subcontracting_record_component]",
        content: _t('Continue'),
        position: "bottom",
    },
    {
        trigger: ".modal-footer .btn-secondary",
        extra_trigger: "button [name=product_qty]:contains(4)",
        content: _t('Discard'),
        position: "bottom",
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.record-components',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        position: "right",
        run: "text 1",
    },

    {
        trigger: ".modal-footer .btn[name=subcontracting_record_component]",
        content: _t('Continue'),
        position: "bottom",
    },

    {
        trigger: ".modal-footer .btn-primary[name=subcontracting_record_component]",
        extra_trigger: "button [name=product_qty]:contains(3)",
        content: _t('Record production'),
        position: "bottom",
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_receipt_flexible_subcontracted_product', {test: true}, [
    {
        trigger: 'button.btn-secondary.o_mrp_subcontracting',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        position: "right",
        run: "text 1",
    },
    {
        trigger: "div[name=move_line_raw_ids] td[name=qty_done]",
    },
    
    {
        trigger: "div[name=move_line_raw_ids] [name=qty_done] input",
        run: "text 2", 
    },
    {
        trigger: ".modal-footer .btn-primary[name=subcontracting_record_component]",
        content: _t('Record production'),
        position: "bottom",
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

});
