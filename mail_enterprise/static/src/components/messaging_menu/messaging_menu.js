/** @odoo-module **/

import { MessagingMenu } from '@mail/components/messaging_menu/messaging_menu';

import { useBackButton } from 'web_mobile.hooks';
import { patch } from 'web.utils';

patch(MessagingMenu.prototype, 'mail_enterprise/static/src/components/chat_window/chat_window.js', {
    /**
     * @override
     */
    setup() {
        this._super();
        this._onBackButtonGlobal = this._onBackButtonGlobal.bind(this);
        useBackButton(this._onBackButtonGlobal, () => this.messagingMenu && this.messagingMenu.isOpen);
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
        if (!this.messagingMenu) {
            return;
        }
        this.messagingMenu.close();
    },
});
