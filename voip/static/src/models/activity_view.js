/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "ActivityView",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickLandlineNumber(ev) {
            ev.preventDefault();
            this.env.services.voip.call({
                number: this.activity.phone,
                activityId: this.activity.id,
                fromActivity: true,
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMobileNumber(ev) {
            if (!this.exists() || !this.component) {
                return;
            }
            ev.preventDefault();
            this.env.services.voip.call({
                number: this.activity.mobile,
                activityId: this.activity.id,
                fromActivity: true,
            });
        },
    },
});
