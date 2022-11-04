/** @odoo-module **/

import { registry } from "@web/core/registry";

import { switchColorSchemeItem } from "./color_scheme_menu_items";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

const colorThemeService = {
    start() {
        userMenuRegistry.add("color_scheme.switch", switchColorSchemeItem);
    },
};
serviceRegistry.add("color_scheme", colorThemeService);
