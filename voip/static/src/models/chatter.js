/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "Chatter",
    lifecycleHooks: {
        _created() {
            this.env.bus.on("voip_reload_chatter", undefined, this._onReload);
        },
        _willDelete() {
            this.env.bus.off("voip_reload_chatter", undefined, this._onReload);
        },
    },
    recordMethods: {
        _onReload() {
            if (!this.thread) {
                return;
            }
            this.thread.fetchData(["activities", "attachments", "messages"]);
        },
    },
});
