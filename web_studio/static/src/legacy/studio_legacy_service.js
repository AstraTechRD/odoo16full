/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const studioLegacyService = {
    dependencies: ["studio"],
    async start(env, { studio }) {
        browser.addEventListener("studio-icon-clicked", () => {
            studio.open();
        });
    }
};

registry.category("services").add("studio_legacy", studioLegacyService);
