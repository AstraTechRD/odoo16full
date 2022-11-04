odoo.define('pos_restaurant_iot.models', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
var PrinterProxy = require('pos_iot.Printer');
const Registries = require('point_of_sale.Registries');

// The override of create_printer needs to happen after its declaration in
// pos_restaurant. We need to make sure that this code is executed after the
// models file in pos_restaurant.
require('pos_restaurant.models');


const PosResIotPosGlobalState = (PosGlobalState) => class PosResIotPosGlobalState extends PosGlobalState {
    create_printer(config) {
        if (config.device_identifier && config.printer_type === "iot"){
            return new PrinterProxy(this, { iot_ip: config.proxy_ip, identifier: config.device_identifier }, this);
        }
        else {
            return super.create_printer(...arguments);
        }
    }
}
Registries.Model.extend(PosGlobalState, PosResIotPosGlobalState);
});
