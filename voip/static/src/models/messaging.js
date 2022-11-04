/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { one } from "@mail/model/model_field";

registerPatch({
    name: "Messaging",
    fields: {
        voip: one("Voip", {
            default: {},
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
