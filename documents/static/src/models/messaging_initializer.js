/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "MessagingInitializer",
    recordMethods: {
        /**
         * @override
         */
        async _init({ hasDocumentsUserGroup }) {
            this.messaging.update({ hasDocumentsUserGroup });
            await this._super(...arguments);
        },
    },
});
