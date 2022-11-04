/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { getCookie, setCookie } from "web.utils.cookies";

export function switchColorSchemeItem(env) {
    return {
        type: "switch",
        id: "color_scheme.switch_theme",
        description: env._t("Dark Mode"),
        callback: () => {
            const cookie = getCookie("color_scheme");
            const theme = cookie === "dark" ? "light" : "dark";
            setCookie("color_scheme", theme);
            browser.location.reload();
        },
        isChecked: getCookie("color_scheme") == "dark" ? true : false,
        sequence: 30,
    };
}
