/** @odoo-module **/

import { Dialog } from '@mail/components/dialog/dialog';
import { useBackButton } from 'web_mobile.hooks';
import { patch } from 'web.utils';

patch(Dialog.prototype, 'mail_enterprise/static/src/components/dialog/dialog.js', {
    /**
     * @override
     */
    setup() {
        this._super();
        this._onBackButtonGlobal = this._onBackButtonGlobal.bind(this);
        this._backButtonHandler = useBackButton(this._onBackButtonGlobal);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the `backbutton` custom event. This event is triggered by the
     * mobile app when the back button of the device is pressed.
     *
     * @private
     * @param {CustomEvent} ev
     */
    _onBackButtonGlobal(ev) {
        if (!this.dialog) {
            return;
        }
        this.dialog.delete();
    },
});
