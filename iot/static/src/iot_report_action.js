/** @odoo-module */
import { registry } from "@web/core/registry";
import { DeviceController } from "@iot/device_controller";


function onIoTActionResult(data, env) {
    if (data.result === true) {
        env.services.notification.add(env._t("Successfully sent to printer!"));
    } else {
        env.services.notification.add(env._t("Check if the printer is still connected"), {
            title: env._t("Connection to printer failed"),
            type: "danger",
        });
    }
}

function onValueChange(data, env) {
    if (data.status) {
        env.services.notification.add(env._t("Printer ") + data.status);
    }
}

async function iotReportActionHandler(action, options, env) {
    if (action.device_id) {
        // Call new route that sends you report to send to printer
        const orm = env.services.orm;
        action.data = action.data || {};
        action.data["device_id"] = action.device_id;
        const args = [action.id, action.context.active_ids, action.data];
        const [ip, identifier, document] = await orm.call("ir.actions.report", "iot_render", args);
        const iotDevice = new DeviceController(env.services.iot_longpolling, { iot_ip: ip, identifier });
        iotDevice.addListener(data => onValueChange(data, env));
        iotDevice.action({ document })
            .then(data => onIoTActionResult(data, env))
            .guardedCatch(() => iotDevice.iotLongpolling._doWarnFail(ip));
        return true;
    }
}

registry
    .category("ir.actions.report handlers")
    .add("iot_report_action_handler", iotReportActionHandler);
