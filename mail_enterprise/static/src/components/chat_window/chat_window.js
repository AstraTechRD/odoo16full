/** @odoo-module **/

import { ChatWindow } from '@mail/components/chat_window/chat_window';

import { useBackButton } from 'web_mobile.hooks';
import { patch } from 'web.utils';

patch(ChatWindow.prototype, 'mail_enterprise/static/src/components/chat_window/chat_window.js', {
    /**
     * @override
     */
    setup() {
        this._super();
        this._onBackButtonGlobal = this._onBackButtonGlobal.bind(this);
        useBackButton(this._onBackButtonGlobal);
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
        if (!this.chatWindow) {
            return;
        }
        this.chatWindow.close();
    },
});
