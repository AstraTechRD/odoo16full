/** @odoo-module */

import { PhoneField } from "@web/views/fields/phone/phone_field";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PhoneField.prototype, "voip.PhoneField", {
    setup() {
        this._super();
        if ("voip" in this.env.services) {
            // FIXME: this is only because otherwise @web tests would fail.
            // This is one of the major pitfalls of patching.
            this.voip = useService("voip");
        }
    },
    /**
     * Called when the phone number is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    async onLinkClicked(ev) {
        if (!this.voip) {
            return;
        }
        if (ev.target.matches("a")) {
            ev.stopImmediatePropagation();
        }
        if (!this.voip.canCall) {
            return;
        }
        ev.preventDefault();
        const { value, record } = this.props;
        this.voip.call({ number: value, resModel: record.resModel, resId: record.resId });
    },
});
