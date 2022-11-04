/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'Messaging',
    fields: {
        /**
         * Registers the system singleton 'social' in global messaging
         * singleton.
         */
        social: one('Social', {
            default: {},
            readonly: true,
            required: true,
        }),
    },
});
