/** @odoo-module **/

/**
 * Modern version of the DeviceProxy from iot.DeviceProxy.
 * It's not dependent to the legacy iot_longpolling service.
 */
export class DeviceController {
    /**
     * @param {Object} iotLongpolling
     * @param {{ iot_ip: string?, identifier: string?, manual_measurement: boolean? }} deviceInfo - Representation of an iot device
     */
    constructor(iotLongpolling, deviceInfo = { iot_ip: null, identifier: null, manual_measurement: null }) {
        this.id = _.uniqueId('listener-');
        this.iotIp = deviceInfo.iot_ip;
        this.identifier = deviceInfo.identifier;
        this.manualMeasurement = deviceInfo.manual_measurement;
        this.iotLongpolling = iotLongpolling;
    }
    action(data) {
        return this.iotLongpolling.action(this.iotIp, this.identifier, data);
    }
    addListener(callback) {
        return this.iotLongpolling.addListener(this.iotIp, [this.identifier], this.id, callback);
    }
    removeListener() {
        return this.iotLongpolling.removeListener(this.iotIp, this.identifier, this.id);
    }
}
