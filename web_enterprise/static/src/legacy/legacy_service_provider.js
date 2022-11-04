/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const legacyServiceProvider = {
    dependencies: ["home_menu"],
    start({ services }) {
        browser.addEventListener("show-home-menu", () => {
            services.home_menu.toggle(true);
        });
    },
};

registry.category("services").add("enterprise_legacy_service_provider", legacyServiceProvider);
