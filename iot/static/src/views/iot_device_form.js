/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { DeviceController } from "../device_controller";
import { Record, RelationalModel } from "@web/views/basic_relational_model";

class IoTDeviceRecord extends Record {
    get iotDevice() {
        if (!this._iotDevice) {
            this._iotDevice = new DeviceController(this.model.iotLongpollingService, {
                iot_ip: this.data.iot_ip,
                identifier: this.data.identifier,
            });
        }
        return this._iotDevice;
    }
    /**
     * @override
     */
    async save() {
        if (["keyboard", "scanner"].includes(this.data.type)) {
            const data = await this.updateKeyboardLayout();
            if (data.result !== true) {
                this.model.dialogService.add(WarningDialog, {
                    title: this.model.env._t("Connection to device failed"),
                    message: this.model.env._t("Check if the device is still connected"),
                });
                // Original logic doesn't call super when reaching this branch.
                return;
            }
        } else if (this.data.type === "display") {
            await this.updateDisplayUrl();
        }
        return await super.save(...arguments);
    }
    /**
     * Send an action to the device to update the keyboard layout
     */
    async updateKeyboardLayout() {
        const keyboard_layout = this.data.keyboard_layout;
        const is_scanner = this.data.is_scanner;
        // IMPROVEMENT: Perhaps combine the call to update_is_scanner and update_layout in just one remote call to the iotbox.
        this.iotDevice.action({ action: "update_is_scanner", is_scanner });
        if (keyboard_layout) {
            const [keyboard] = await this.model.orm.read(
                "iot.keyboard.layout",
                [keyboard_layout[0]],
                ["layout", "variant"]
            );
            return this.iotDevice.action({
                action: "update_layout",
                layout: keyboard.layout,
                variant: keyboard.variant,
            });
        } else {
            return this.iotDevice.action({ action: "update_layout" });
        }
    }
    /**
     * Send an action to the device to update the screen url
     */
    updateDisplayUrl() {
        const display_url = this.data.display_url;
        return this.iotDevice.action({ action: "update_url", url: display_url });
    }
}

class IoTDeviceModel extends RelationalModel {
    setup(params, services) {
        this.iotLongpollingService = services.iot_longpolling;
        super.setup(...arguments);
    }
}
IoTDeviceModel.Record = IoTDeviceRecord;
IoTDeviceModel.services = [...RelationalModel.services, "iot_longpolling"];

export const iotDeviceFormView = {
    ...formView,
    Model: IoTDeviceModel,
};

registry.category("views").add("iot_device_form", iotDeviceFormView);
