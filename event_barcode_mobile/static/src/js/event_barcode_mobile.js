odoo.define('web.event.barcode_mobile', function (require) {
"use strict";

const EventBarcodeScanView = require('event_barcode.EventScanView');
const barcodeMobileMixin = require('web_mobile.barcode_mobile_mixin');

EventBarcodeScanView.include(Object.assign({}, barcodeMobileMixin, {
    events: Object.assign({}, barcodeMobileMixin.events, EventBarcodeScanView.prototype.events)
}));
});
