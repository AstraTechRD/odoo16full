/** @odoo-module **/

/**
 * This file can be removed as soon as voip code will be converted to 
 */

import { browser } from "@web/core/browser/browser";
import { ComponentAdapter } from "web.OwlCompatibility";
import core from "web.core";
import { useBus } from "@web/core/utils/hooks";

const { Component } = owl;

/**
 * Specialization of a ComponentAdapter for the DialingPanel. Uses the voip
 * service to toggle the legacy DialingPanel.
 */
export class DialingPanelAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.env = Component.env;

        const voipBus = this.props.bus;

        useBus(voipBus, "TOGGLE_DIALING_PANEL", () => {
            core.bus.trigger('voip_onToggleDisplay');
        });

        useBus(voipBus, "VOIP-CALL", (ev) => {
            const payload = ev.detail;
            if (payload.fromActivity) {
                this.widget.callFromActivityWidget(payload);
            } else {
                this.widget.callFromPhoneWidget(payload);
            }
        });
    }
}

/**
 * Service that redirects events triggered up by e.g. the FieldPhone to the
 * DialingPanel.
 */
export const voipLegacyCompatibilityService = {
    dependencies: ["voip"],
    start(env, { voip }) {
        browser.addEventListener("voip-call", (ev) => {
            voip.call(ev.detail);
        });
        browser.addEventListener("voip-activity-call", (ev) => {
            const params = Object.assign({}, ev.detail, { fromActivity: true});
            voip.call(params);
        });
    },
};
