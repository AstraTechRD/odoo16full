odoo.define('web_mobile.barcode_mobile_mixin', function (require) {
"use strict";

const BarcodeScanner = require('@web/webclient/barcode/barcode_scanner');
const core = require('web.core');
const _t = core._t;

return {
    events: {
        'click .o_mobile_barcode': 'open_mobile_scanner'
    },
    async start() {
        const res = await this._super(...arguments);
        if (!BarcodeScanner.isBarcodeScannerSupported()) {
            this.$el.find(".o_mobile_barcode").remove();
        }
        return res;
    },
    getFacingMode() {
        return 'environment';
    },
    async open_mobile_scanner() {
        let error = null;
        let barcode = null;
        try {
            barcode = await BarcodeScanner.scanBarcode(this.getFacingMode());
        } catch (err) {
            error = err.error.message;
        }

        if (barcode) {
            this._onBarcodeScanned(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.displayNotification({
                type: 'warning',
                message: error || _t('Please, Scan again !'),
            });
        }
    }
};
});
