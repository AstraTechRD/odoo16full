/** @odoo-module **/

import Tablet from '@mrp_workorder/components/tablet';
import { patch } from '@web/core/utils/patch';
import { DeviceController } from '@iot/device_controller';
import { PedalStatusButton } from '@mrp_workorder_iot/pedal_status_button/pedal_status_button';

const { onWillUnmount } = owl;

const unpatchTabletPrototypeOverride = patch(Tablet.prototype, 'tablet_iot', {
    setup() {
        this._super();
        this.state.pedalConnected = false;
        this.state.showPedalStatus = false;
        this.deviceControllers = {};
        onWillUnmount(() => {
            this.onWillUnmount();
        });
    },
    async _onWillStart() {
        await this._super();
        // Start listening to the iot devices.
        const box2device2key2action = {};
        for (const check of this.data['quality.check']) {
            if (!check.boxes) {
                continue;
            }
            const triggers = JSON.parse(check.boxes);
            for (const iot_box_ip in triggers) {
                if (!(iot_box_ip in box2device2key2action)) {
                    box2device2key2action[iot_box_ip] = {};
                }
                const device2key2action = box2device2key2action[iot_box_ip];
                for (const [identifier, key, action] of triggers[iot_box_ip]) {
                    if (!(identifier in device2key2action)) {
                        device2key2action[identifier] = {};
                    }
                    device2key2action[identifier][key] = action;
                }
            }
        }
        for (const iot_box_ip in box2device2key2action) {
            const device2key2action = box2device2key2action[iot_box_ip];
            for (const deviceIdentifier in device2key2action) {
                // Show the pedal status button once there is a device controller instantiated.
                this.state.showPedalStatus = true;
                const controller = new DeviceController(this.env.services.iot_longpolling, {
                    identifier: deviceIdentifier,
                    iot_ip: iot_box_ip,
                });
                controller.addListener(this.createOnValueChangeHandler(device2key2action[deviceIdentifier]));
                this.deviceControllers[`${iot_box_ip}/${deviceIdentifier}`] = controller;
            }
        }
        return this.takeOwnership();
    },
    onWillUnmount() {
        // Stop listening to the iot devices.
        for (const controller of Object.values(this.deviceControllers)) {
            controller.removeListener();
        }
    },
    createOnValueChangeHandler(key2action) {
        return (data) => {
            if (data.owner && data.owner !== data.session_id) {
                this.state.pedalConnected = false;
            } else {
                for (const key in key2action) {
                    if (data.value === key) {
                        this.barcode.bus.trigger('barcode_scanned', { barcode: `O-BTN.${key2action[key]}` });
                    }
                }
            }
        };
    },
    async takeOwnership() {
        for (const controller of Object.values(this.deviceControllers)) {
            await controller.action({});
        }
        this.state.pedalConnected = true;
    },
});

const unpatchTabletClassOverride = patch(Tablet, 'tablet_iot', {
    components: { ...Tablet.components, PedalStatusButton },
});

export const unpatchTablet = () => {
    unpatchTabletPrototypeOverride();
    unpatchTabletClassOverride();
};
