odoo.define('stock_barcode.RunningTourActionHelper', function(require) {
"use strict";

var RunningTourActionHelper = require('web_tour.RunningTourActionHelper');

RunningTourActionHelper.include({
    _scan: function (element, barcode) {
        odoo.__DEBUG__.services['web.core'].bus.trigger('barcode_scanned', barcode, element);
    },
    scan: function(barcode, element) {
        this._scan(this._get_action_values(element), barcode);
    },
});

const StepUtils = require('web_tour.TourStepUtils');
StepUtils.include({
    closeModal() {
        return {
            trigger: '.btn.btn-primary',
            in_modal: true,
        };
    },
    confirmAddingUnreservedProduct() {
        return {
            trigger: '.btn-primary',
            extra_trigger: '.modal-title:contains("Add extra product?")',
            in_modal: true,
        };
    },
    validateBarcodeForm() {
        return [{
            trigger: '.o_barcode_client_action',
            run: 'scan O-BTN.validate'
        }, {
            trigger: '.o_notification.border-success',
        }];
    },
    discardBarcodeForm() {
        return [{
            content: "discard barcode form",
            trigger: '.o_discard',
            auto: true,
        }, {
            content: "wait to be back on the barcode lines",
            trigger: '.o_add_line',
            auto: true,
            run() {},
        }];
    },
});

});
