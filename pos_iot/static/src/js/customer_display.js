odoo.define('pos_iot.customer_display', function (require) {
"use strict";

var ProxyDevice = require('point_of_sale.devices').ProxyDevice;

ProxyDevice.include({
    update_customer_facing_display: function(html) {
        if (this.env.proxy.iot_device_proxies.display) {
            return this.env.proxy.iot_device_proxies.display.action({
                action: 'customer_facing_display',
                html: html,
            });
        }
    },

    take_ownership_over_customer_screen: function(html) {
        return this.env.proxy.iot_device_proxies.display.action({
            action: "take_control",
            html: html,
        });
    },
});
});
