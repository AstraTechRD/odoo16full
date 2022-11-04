/** @odoo-module **/

import "@mail/../tests/helpers/mock_server"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "voip", {
    /**
     * @override
     * @returns {Object}
     */
    _mockResUsers_InitMessaging(...args) {
        return {
            ...this._super(...args),
            voipConfig: {
                mode: this.getRecords("ir.config_parameter", [["key", "=", "voip.mode"]])[0].value,
                pbxAddress: this.getRecords("ir.config_parameter", [["key", "=", "voip.pbx_ip"]])[0].value,
                webSocketUrl: this.getRecords("ir.config_parameter", [["key", "=", "voip.wsServer"]])[0].value,
            },
        };
    },
});
