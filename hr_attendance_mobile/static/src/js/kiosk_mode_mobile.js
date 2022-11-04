odoo.define('hr_attendance.kiosk_mode_barcode_mobile', function (require) {
"use strict";

const KioskMode = require('hr_attendance.kiosk_mode');
const barcodeMobileMixin = require('web_mobile.barcode_mobile_mixin');

KioskMode.include(Object.assign({}, barcodeMobileMixin, {
    events: Object.assign({}, barcodeMobileMixin.events, KioskMode.prototype.events),
    getFacingMode() {
        if (this.barcode_source == 'front') {
            return 'user';
        }
        return barcodeMobileMixin.getFacingMode();
    }
}));
});
