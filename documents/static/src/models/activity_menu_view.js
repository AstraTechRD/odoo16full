/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ActivityMenuView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onClickRequestDocument(ev) {
            this.update({ isOpen: false });
            this.env.services.action.doAction('documents.action_request_form');
        },
    },
});
