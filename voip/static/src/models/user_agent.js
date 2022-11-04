/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";

registerModel({
    name: "UserAgent",
    fields: {
        legacyUserAgent: attr(),
        registerer: one("Registerer", {
            inverse: "userAgent",
        }),
        voip: one("Voip", {
            identifying: true,
            inverse: "userAgent",
        }),
        __sipJsUserAgent: attr(),
    },
});
