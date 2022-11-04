/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'Messaging',
    fields: {
        /**
         * Registers the system singleton 'knowledge' in global messaging
         * singleton.
         */
        knowledge: one('Knowledge', {
            default: {},
            readonly: true,
            required: true,
        }),
    },
});
