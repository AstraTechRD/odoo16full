odoo.define('iot.DeviceProxy', function (require) {
'use strict';

var core = require('web.core');
const ServicesMixin = require('web.ServicesMixin');
const { EventDispatcherMixin } = require('web.mixins');


/**
 * Frontend interface to iot devices
 * TODO: This can be replaced by the new DeviceController.
 */
var DeviceProxy = core.Class.extend(EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {Object} iot_device - Representation of an iot device
     * @param {string} iot_device.iot_ip - The ip address of the iot box the device is connected to
     * @param {string} iot_device.identifier - The device's unique identifier
     */
    init: function(parent, iot_device) {
        EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);
        this._id = _.uniqueId('listener-');
        this._iot_ip = iot_device.iot_ip;
        this._identifier = iot_device.identifier;
        this.manual_measurement = iot_device.manual_measurement;
    },

    /**
     * Call actions on the device
     * @param {Object} data
     * @returns {Promise}
     */
    action: function(data) {
        return this.call('iot_longpolling', 'action', this._iot_ip, this._identifier, data);
    },

    /**
     * Add `callback` to the listeners callbacks list it gets called everytime the device's value is updated.
     * @param {function} callback
     * @returns {Promise}
     */
    add_listener: function(callback) {
        return this.call('iot_longpolling', 'addListener', this._iot_ip, [this._identifier, ], this._id, callback);
    },
    /**
     * Stop listening the device
     */
    remove_listener: function() {
        return this.call('iot_longpolling', 'removeListener', this._iot_ip, this._identifier, this._id);
    },
});

return DeviceProxy;

});
