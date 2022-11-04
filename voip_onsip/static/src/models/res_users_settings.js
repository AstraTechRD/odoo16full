/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import { attr } from "@mail/model/model_field";

registerPatch({
    name: "res.users.settings",
    fields: {
        onsip_auth_username: attr(),
    },
});
